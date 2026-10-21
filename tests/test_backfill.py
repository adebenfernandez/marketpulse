"""Tests de la carga histórica. El HttpClient es un mock: no se llama a ninguna API real."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from marketpulse.common.config import load_watchlist
from marketpulse.ingest import backfill
from marketpulse.ingest.errors import UnexpectedResponseError

WATCHLIST = load_watchlist()
DIA = date(2026, 10, 21)
FX = [
    {"date": "2025-10-20", "base": "EUR", "quote": "GBP", "rate": 0.8691},
    {"date": "2025-10-20", "base": "EUR", "quote": "USD", "rate": 1.1655},
]
CHART = {
    "prices": [[1761091200000, 108301.7]],
    "market_caps": [[1761091200000, 2.1e12]],
    "total_volumes": [[1761091200000, 5.0e10]],
}


def client_que_responde():
    """Frankfurter devuelve FX; cualquier URL de CoinGecko devuelve CHART."""
    client = MagicMock()
    client.get_json.side_effect = lambda url, **kw: FX if "frankfurter" in url else CHART
    return client


def test_pide_un_anio_al_bce_en_una_sola_peticion():
    client = client_que_responde()
    backfill.fetch_fx_history(client, WATCHLIST.fx, date(2025, 10, 21), DIA)
    client.get_json.assert_called_once_with(
        "https://api.frankfurter.dev/v2/rates",
        params={
            "base": "EUR",
            "quotes": "USD,GBP",
            "providers": "ECB",
            "from": "2025-10-21",
            "to": "2026-10-21",
        },
    )


def test_pide_365_dias_diarios_a_coingecko_con_la_clave_en_la_cabecera():
    client = client_que_responde()
    backfill.fetch_crypto_history(client, "bitcoin", "usd", "clave-demo")
    client.get_json.assert_called_once_with(
        "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
        params={"vs_currency": "usd", "days": "365", "interval": "daily"},
        headers={"x-cg-demo-api-key": "clave-demo"},
    )


def test_coingecko_sin_series_falla_sin_escribir():
    client = MagicMock()
    client.get_json.return_value = {"prices": []}
    with pytest.raises(UnexpectedResponseError, match="bitcoin"):
        backfill.fetch_crypto_history(client, "bitcoin", "usd", None)


def test_guarda_en_fuentes_propias_un_fichero_por_moneda(tmp_path):
    paths = backfill.run_backfill(client_que_responde(), WATCHLIST, "k", dt=DIA, root=tmp_path)
    rel = sorted(p.relative_to(tmp_path).as_posix() for p in paths)
    assert rel == [
        "bronze/source=coingecko_backfill/dt=2026-10-21/bitcoin.json",
        "bronze/source=coingecko_backfill/dt=2026-10-21/ethereum.json",
        "bronze/source=coingecko_backfill/dt=2026-10-21/solana.json",
        "bronze/source=frankfurter_backfill/dt=2026-10-21/frankfurter.json",
    ]


def test_repetir_el_backfill_no_duplica(tmp_path):
    for _ in range(2):
        backfill.run_backfill(client_que_responde(), WATCHLIST, "k", dt=DIA, root=tmp_path)
    assert len(list((tmp_path / "bronze").rglob("*.json"))) == 4
