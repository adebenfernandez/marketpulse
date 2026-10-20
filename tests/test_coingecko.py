"""Tests del cliente de CoinGecko. El HttpClient es un mock: no se llama a la API real."""

import json
import logging
from datetime import date
from unittest.mock import MagicMock

import pytest

from marketpulse.common.config import CryptoAsset, CryptoConfig
from marketpulse.ingest import coingecko
from marketpulse.ingest.errors import UnexpectedResponseError

CRYPTO = CryptoConfig(
    vs_currency="usd",
    assets=(
        CryptoAsset("BTC", "bitcoin"),
        CryptoAsset("ETH", "ethereum"),
        CryptoAsset("SOL", "solana"),
    ),
)
DIA = date(2026, 10, 20)

# Forma de una respuesta real (20/10/2026)
RESPUESTA_REAL = {
    "bitcoin": {"usd": 82388, "usd_market_cap": 1.6e12, "usd_24h_vol": 2.9e10,
                "usd_24h_change": -1.41, "last_updated_at": 1792509891},
    "ethereum": {"usd": 2431.74, "usd_market_cap": 2.9e11, "usd_24h_vol": 1.5e10,
                 "usd_24h_change": 0.52, "last_updated_at": 1792509877},
    "solana": {"usd": 105.25, "usd_market_cap": 5.6e10, "usd_24h_vol": 3.1e9,
               "usd_24h_change": 2.03, "last_updated_at": 1792509881},
}  # fmt: skip


def mock_client(respuesta) -> MagicMock:
    client = MagicMock()
    client.get_json.return_value = respuesta
    return client


def test_pide_todas_las_monedas_en_una_sola_llamada():
    client = mock_client(RESPUESTA_REAL)
    coingecko.fetch_prices(client, CRYPTO)
    client.get_json.assert_called_once()
    params = client.get_json.call_args.kwargs["params"]
    assert params["ids"] == "bitcoin,ethereum,solana"
    assert params["vs_currencies"] == "usd"
    assert params["include_last_updated_at"] == "true"


def test_sin_clave_no_envia_cabecera():
    client = mock_client(RESPUESTA_REAL)
    coingecko.fetch_prices(client, CRYPTO, api_key=None)
    assert client.get_json.call_args.kwargs["headers"] is None


def test_con_clave_la_envia_en_cabecera_y_no_en_la_url():
    client = mock_client(RESPUESTA_REAL)
    coingecko.fetch_prices(client, CRYPTO, api_key="CLAVE-DE-PRUEBA")
    kwargs = client.get_json.call_args.kwargs
    assert kwargs["headers"] == {"x-cg-demo-api-key": "CLAVE-DE-PRUEBA"}
    assert "CLAVE-DE-PRUEBA" not in json.dumps(kwargs["params"])


def test_ingest_guarda_la_respuesta_en_su_particion(tmp_path):
    path = coingecko.ingest(mock_client(RESPUESTA_REAL), CRYPTO, dt=DIA, root=tmp_path)
    assert path == tmp_path / "bronze" / "source=coingecko" / "dt=2026-10-20" / "coingecko.json"
    assert json.loads(path.read_text(encoding="utf-8")) == RESPUESTA_REAL


@pytest.mark.parametrize(
    "respuesta",
    [
        {},  # vacío
        [],  # una lista en vez de un diccionario
        {"bitcoin": {"eur": 70000}},  # precio en otra moneda
        {"status": {"error_code": 10002, "error_message": "No API key"}},  # aviso, no datos
    ],
)
def test_respuesta_con_forma_inesperada_da_error_y_no_escribe(tmp_path, respuesta):
    with pytest.raises(UnexpectedResponseError):
        coingecko.ingest(mock_client(respuesta), CRYPTO, dt=DIA, root=tmp_path)
    assert not (tmp_path / "bronze").exists()


def test_avisa_si_falta_un_id(caplog):
    caplog.set_level(logging.WARNING)
    sin_solana = {k: v for k, v in RESPUESTA_REAL.items() if k != "solana"}
    assert coingecko.fetch_prices(mock_client(sin_solana), CRYPTO) == sin_solana
    assert "solana" in caplog.text
