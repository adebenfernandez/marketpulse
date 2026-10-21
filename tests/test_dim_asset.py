"""Tests de la dimensión de activos (modelo en estrella, Fase 4)."""

import pandas as pd
import pyarrow.parquet as pq

from marketpulse.common.config import load_watchlist
from marketpulse.quality.rules import check_dim_asset, has_errors
from marketpulse.transform import gold

WATCHLIST = load_watchlist()


def test_una_fila_por_activo_de_la_watchlist_con_sus_atributos():
    dim = gold.dim_asset_from(WATCHLIST)
    assert set(dim["asset"]) == set(gold.watchlist_assets(WATCHLIST))  # misma lista que gold
    btc = dim.set_index("asset").loc["BTC"]
    assert (btc["asset_name"], btc["currency"], btc["price_type"]) == ("Bitcoin", "USD", "snapshot")
    assert btc["annualization_days"] == 365
    eur_gbp = dim.set_index("asset").loc["EUR/GBP"]
    assert (eur_gbp["currency"], eur_gbp["annualization_days"]) == ("GBP", 252)


def test_hechos_y_dimension_dicen_lo_mismo_de_cada_clase():
    # La moneda, el tipo de precio y la fuente salen de las MISMAS constantes en las dos tablas
    dim = gold.dim_asset_from(WATCHLIST).set_index("asset")
    spy = gold.equity_daily(pd.DataFrame({"date": [None], "symbol": ["SPY"], "close": [1.0]}))
    assert spy.iloc[0]["price_type"] == dim.loc["SPY", "price_type"]
    assert spy.iloc[0]["source"] == dim.loc["SPY", "source"]


def test_se_escribe_en_un_solo_parquet_sin_particiones(tmp_path):
    gold.write_dim_asset(gold.dim_asset_from(WATCHLIST), tmp_path)
    files = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*.parquet"))
    assert files == ["gold/dim_asset/part-0.parquet"]
    schema = pq.read_schema(tmp_path / files[0])
    assert str(schema.field("annualization_days").type) == "int32"


def test_un_activo_en_los_hechos_que_no_esta_en_la_dimension_es_error():
    dim = gold.dim_asset_from(WATCHLIST)
    hechos = pd.DataFrame({"asset": ["BTC", "DOGE"]})
    results = check_dim_asset(dim, hechos)
    assert has_errors(results)
    fallo = next(r for r in results if not r.passed)
    assert fallo.table == "daily_prices->dim_asset"


def test_dimension_correcta_pasa():
    dim = gold.dim_asset_from(WATCHLIST)
    assert not has_errors(check_dim_asset(dim, pd.DataFrame({"asset": ["BTC", "SPY"]})))
