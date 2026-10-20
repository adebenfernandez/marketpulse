"""Tests del cliente de Alpha Vantage. El HttpClient es un mock: no se llama a la API real."""

import json
from datetime import date
from unittest.mock import MagicMock

import pytest

from marketpulse.common.config import StockAsset, StocksConfig
from marketpulse.common.http import HttpError
from marketpulse.ingest import alphavantage
from marketpulse.ingest.errors import (
    MissingApiKeyError,
    PartialIngestError,
    UnexpectedResponseError,
)

STOCKS = StocksConfig(assets=(StockAsset("SPY", ""), StockAsset("VT", "")))
DIA = date(2026, 10, 20)
CLAVE = "CLAVE-DE-PRUEBA"  # inventada: nunca una clave real en los tests


def serie(symbol: str) -> dict:
    """Respuesta con la forma real de TIME_SERIES_DAILY (comprobada el 20/10/2026)."""
    return {
        "Meta Data": {
            "1. Information": "Daily Prices (open, high, low, close) and Volumes",
            "2. Symbol": symbol,
            "3. Last Refreshed": "2026-10-19",
            "4. Output Size": "Compact",
            "5. Time Zone": "US/Eastern",
        },
        "Time Series (Daily)": {
            "2026-10-19": {"1. open": "580.10", "2. high": "583.00", "3. low": "578.20",
                           "4. close": "582.40", "5. volume": "51234567"},
            "2026-10-16": {"1. open": "577.00", "2. high": "580.50", "3. low": "575.10",
                           "4. close": "579.90", "5. volume": "48765432"},
        },
    }  # fmt: skip


def no_sleep(seconds: float) -> None:
    """Sustituye a time.sleep en los tests: no queremos esperar de verdad."""


def mock_client(*respuestas) -> MagicMock:
    client = MagicMock()
    client.get_json.side_effect = list(respuestas)  # una respuesta por llamada, en orden
    return client


def test_pide_la_serie_diaria_compacta_de_cada_simbolo(tmp_path):
    client = mock_client(serie("SPY"), serie("VT"))
    alphavantage.ingest(client, STOCKS, CLAVE, dt=DIA, root=tmp_path, sleep=no_sleep)
    assert client.get_json.call_count == 2
    params = client.get_json.call_args_list[0].kwargs["params"]
    assert params == {
        "function": "TIME_SERIES_DAILY",
        "symbol": "SPY",
        "outputsize": "compact",
        "apikey": CLAVE,
    }


def test_un_fichero_por_simbolo_en_la_misma_particion(tmp_path):
    paths = alphavantage.ingest(
        mock_client(serie("SPY"), serie("VT")), STOCKS, CLAVE, dt=DIA, root=tmp_path, sleep=no_sleep
    )
    carpeta = tmp_path / "bronze" / "source=alphavantage" / "dt=2026-10-20"
    assert paths == [carpeta / "SPY.json", carpeta / "VT.json"]
    assert json.loads(paths[0].read_text(encoding="utf-8")) == serie("SPY")


def test_sin_clave_no_hace_ninguna_llamada(tmp_path):
    client = mock_client()
    with pytest.raises(MissingApiKeyError, match="ALPHAVANTAGE_API_KEY"):
        alphavantage.ingest(client, STOCKS, api_key="", dt=DIA, root=tmp_path)
    client.get_json.assert_not_called()


@pytest.mark.parametrize(
    "aviso",
    [
        {"Information": "We have detected your API key ... 25 requests per day."},  # límite diario
        {"Note": "Thank you for using Alpha Vantage! ..."},  # aviso antiguo de límite
        {"Error Message": "Invalid API call. Please retry or visit the documentation."},
        {"Meta Data": {}},  # falta la serie
        {"Meta Data": {}, "Time Series (Daily)": {}},  # serie vacía
    ],
)
def test_un_200_con_aviso_es_un_error(aviso):
    with pytest.raises(UnexpectedResponseError):
        alphavantage.fetch_daily(mock_client(aviso), "SPY", CLAVE)


def test_si_el_aviso_repite_la_clave_se_tapa():
    client = mock_client({"Error Message": f"the apikey {CLAVE} is invalid"})
    with pytest.raises(UnexpectedResponseError) as excinfo:
        alphavantage.fetch_daily(client, "SPY", CLAVE)
    assert CLAVE not in str(excinfo.value)


def test_si_falla_un_simbolo_guarda_los_demas_y_lo_avisa(tmp_path):
    client = mock_client({"Error Message": "Invalid API call"}, serie("VT"))
    with pytest.raises(PartialIngestError) as excinfo:
        alphavantage.ingest(client, STOCKS, CLAVE, dt=DIA, root=tmp_path, sleep=no_sleep)

    assert list(excinfo.value.failed) == ["SPY"]  # dice qué falló
    carpeta = tmp_path / "bronze" / "source=alphavantage" / "dt=2026-10-20"
    assert (carpeta / "VT.json").exists()  # VT sí se guardó
    assert not (carpeta / "SPY.json").exists()  # y SPY no tiene basura


def test_un_error_http_tambien_cuenta_como_fallo_del_simbolo(tmp_path):
    client = mock_client(HttpError("GET ... devolvió 503", 503), serie("VT"))
    with pytest.raises(PartialIngestError) as excinfo:
        alphavantage.ingest(client, STOCKS, CLAVE, dt=DIA, root=tmp_path, sleep=no_sleep)
    assert "503" in excinfo.value.failed["SPY"]


def test_espera_entre_peticiones_para_no_superar_1_por_segundo(tmp_path):
    stocks = StocksConfig(
        assets=(StockAsset("SPY", ""), StockAsset("VT", ""), StockAsset("QQQ", ""))
    )
    waits: list[float] = []
    client = mock_client(serie("SPY"), serie("VT"), serie("QQQ"))
    alphavantage.ingest(client, stocks, CLAVE, dt=DIA, root=tmp_path, sleep=waits.append)
    assert waits == [1.5, 1.5]  # 3 peticiones -> 2 pausas (ninguna antes de la primera)
