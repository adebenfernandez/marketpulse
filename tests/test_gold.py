"""Tests de silver -> gold. Se construye un silver real a partir de un bronze falso."""

from datetime import date
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from marketpulse.common.config import load_watchlist
from marketpulse.common.storage import write_bronze
from marketpulse.transform import gold, run, silver
from marketpulse.transform.tables import read_table

WATCHLIST_PATH = Path(__file__).resolve().parents[1] / "config" / "watchlist.yaml"
WATCHLIST = load_watchlist(WATCHLIST_PATH)
D20 = date(2026, 10, 20)


@pytest.fixture
def lake(tmp_path):
    """Bronze de un día con las tres fuentes, ya transformado a silver."""
    fx = [
        {"date": "2026-10-20", "base": "EUR", "quote": "USD", "rate": 1.1215},
        {"date": "2026-10-20", "base": "EUR", "quote": "GBP", "rate": 0.84028},
    ]
    write_bronze("frankfurter", fx, dt=D20, root=tmp_path)
    cg = {
        "bitcoin": {"usd": 82388.0, "usd_market_cap": 1.6e12, "usd_24h_vol": 2.7e10,
                    "usd_24h_change": 0.5, "last_updated_at": 1792509891},
    }  # fmt: skip
    write_bronze("coingecko", cg, dt=D20, root=tmp_path)
    av = {
        "Meta Data": {"2. Symbol": "SPY"},
        "Time Series (Daily)": {
            "2026-10-19": {"1. open": "760", "2. high": "770", "3. low": "759",
                           "4. close": "766.48", "5. volume": "41000000"},
        },
    }  # fmt: skip
    write_bronze("alphavantage", av, dt=D20, name="SPY", root=tmp_path)
    silver.build_silver(WATCHLIST, root=tmp_path)
    return tmp_path


def test_una_fila_por_dia_y_activo_con_las_tres_clases(lake):
    df = gold.build_daily_prices(WATCHLIST, root=lake)
    assert sorted(df["asset"]) == ["BTC", "EUR/GBP", "EUR/USD", "SPY"]
    assert not df.duplicated(["date", "asset"]).any()
    assert set(df["asset_class"]) == {"crypto", "equity", "fx"}


def test_cada_clase_lleva_su_precio_moneda_y_tipo(lake):
    df = gold.build_daily_prices(WATCHLIST, root=lake).set_index("asset")
    assert df.loc["SPY", ["price", "currency", "price_type"]].tolist() == [766.48, "USD", "close"]
    assert df.loc["BTC", ["price", "currency", "price_type"]].tolist() == [
        82388.0,
        "USD",
        "snapshot",
    ]
    # EUR/GBP = 0,84 -> 1 EUR vale 0,84 GBP: el precio está en GBP (la quote), no en EUR
    eur_gbp = df.loc["EUR/GBP", ["price", "currency", "price_type"]].tolist()
    assert eur_gbp == [0.84028, "GBP", "reference_rate"]


def test_cripto_solo_en_la_moneda_de_la_watchlist(lake):
    crypto = read_table(lake / "silver" / "crypto_prices")
    otra = crypto.assign(vs_currency="eur", price=70000.0)
    doble = gold.crypto_daily(pd.concat([crypto, otra], ignore_index=True), "usd")
    assert len(doble) == 1 and doble.iloc[0]["currency"] == "USD"


def test_build_gold_escribe_parquet_con_el_esquema(lake):
    written = gold.build_gold(WATCHLIST, root=lake)
    schema = pq.read_schema(written["daily_prices"] / "year=2026" / "part-0.parquet")
    assert schema.field("date").type == pa.date32()
    assert schema.field("price").type == pa.float64()
    assert "volume" not in schema.names  # a propósito: unidades distintas según la clase


def test_sin_silver_no_se_escribe_gold(tmp_path):
    assert gold.build_gold(WATCHLIST, root=tmp_path) == {}


@pytest.mark.parametrize(("publicado", "codigo"), [(True, 0), (False, 1)])
def test_main_de_transform_devuelve_el_codigo_de_salida(monkeypatch, publicado, codigo):
    # run_transform se prueba a fondo en test_quality.py; aquí solo el código de salida
    monkeypatch.setenv("MARKETPULSE_WATCHLIST", str(WATCHLIST_PATH))
    monkeypatch.setattr(run, "run_transform", lambda watchlist: publicado)
    assert run.main() == codigo


def test_watchlist_assets_da_la_clase_de_cada_activo():
    assets = gold.watchlist_assets(WATCHLIST)
    assert assets["BTC"] == "crypto" and assets["SPY"] == "equity" and assets["EUR/USD"] == "fx"
    assert len(assets) == 3 + 3 + 2  # la watchlist real: 3 cripto, 3 ETF, 2 pares
