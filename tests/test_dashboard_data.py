"""Tests de la capa de datos del dashboard (paso 8.3, D-040), con un Athena FALSO."""

import pandas as pd
import pytest

from dashboard.data import (
    ASSETS_SQL,
    MAX_DAYS,
    PRICES_SQL,
    ROW_LIMIT,
    VOLATILITY_SQL,
    latest_volatility,
    load_assets,
    load_prices,
    load_volatility,
    rebase_to_100,
)
from marketpulse.agent.guard import validate_sql
from tests.test_athena import FakeAthena

PRICE_ROWS = [
    ["date", "asset", "asset_class", "price", "currency"],
    ["2026-10-24", "BTC", "crypto", "83576.13", "USD"],
    ["2026-10-25", "BTC", "crypto", "84010.5", "USD"],
    ["2026-10-23", "SPY", "equity", "671.2", "USD"],
]


def test_los_precios_llegan_con_tipos_de_fecha_y_numero():
    df = load_prices(FakeAthena(["SUCCEEDED"], rows=PRICE_ROWS), days=30)
    assert list(df.columns) == ["date", "asset", "asset_class", "price", "currency"]
    assert len(df) == 3
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert df["price"].dtype == "float64"
    assert df.loc[1, "price"] == 84010.5


def test_la_sql_pasa_por_el_validador_y_lleva_limit():
    athena = FakeAthena(["SUCCEEDED"], rows=PRICE_ROWS)
    load_prices(athena, days=30)
    sql = athena.started[0]["QueryString"]
    assert "daily_prices" in sql
    assert "-30" in sql  # los días van dentro de la SQL...
    assert sql.endswith(f"LIMIT {ROW_LIMIT}")  # ...y el validador añade el LIMIT


@pytest.mark.parametrize("days", [0, -5, MAX_DAYS + 1, "30", "30; DROP TABLE x", 7.5, True, None])
def test_dias_no_validos_no_llegan_a_athena(days):
    athena = FakeAthena(["SUCCEEDED"], rows=PRICE_ROWS)
    with pytest.raises(ValueError):
        load_prices(athena, days=days)
    assert athena.started == []


def test_un_valor_que_no_es_un_numero_falla_en_vez_de_quedar_vacio():
    rows = [PRICE_ROWS[0], ["2026-10-25", "BTC", "crypto", "no-es-un-precio", "USD"]]
    with pytest.raises(ValueError):
        load_prices(FakeAthena(["SUCCEEDED"], rows=rows))


def test_sin_filas_devuelve_una_tabla_vacia_con_columnas():
    rows = [["date", "asset", "asset_class", "annualized_volatility_30"]]
    df = load_volatility(FakeAthena(["SUCCEEDED"], rows=rows))
    assert df.empty
    assert "annualized_volatility_30" in df.columns
    assert latest_volatility(df).empty


def test_la_ultima_volatilidad_es_la_de_cada_activo_aunque_la_bolsa_vaya_un_dia_atras():
    rows = [
        ["date", "asset", "asset_class", "annualized_volatility_30"],
        ["2026-10-24", "BTC", "crypto", "0.20"],
        ["2026-10-25", "BTC", "crypto", "0.23"],
        ["2026-10-23", "SPY", "equity", "0.15"],  # la bolsa aún no tiene el cierre del 24 ni 25
        ["2026-10-25", "SOL", "crypto", "0.41"],
    ]
    last = latest_volatility(load_volatility(FakeAthena(["SUCCEEDED"], rows=rows)))
    assert list(last["asset"]) == ["SOL", "BTC", "SPY"]  # de mayor a menor
    assert last.loc[1, "annualized_volatility_30"] == 0.23  # la última de BTC, no la del 24
    assert last.loc[2, "date"] == pd.Timestamp("2026-10-23")  # SPY no se queda fuera


def test_base_100_compara_activos_de_escalas_muy_distintas():
    prices = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-10-02", "2026-10-01", "2026-10-01", "2026-10-02"]),
            "asset": ["BTC", "BTC", "EUR/GBP", "EUR/GBP"],
            "price": [88000.0, 80000.0, 0.80, 0.84],  # desordenado a propósito
        }
    )
    out = rebase_to_100(prices)
    by_asset = out.groupby("asset")["index_100"].apply(list).to_dict()
    assert by_asset["BTC"] == pytest.approx([100.0, 110.0])  # empieza en 100 y sube un 10 %
    assert by_asset["EUR/GBP"] == pytest.approx([100.0, 105.0])
    assert rebase_to_100(prices.iloc[0:0]).empty


def test_los_activos_vienen_tal_cual():
    rows = [["asset", "asset_name", "asset_class", "currency"], ["BTC", "Bitcoin", "crypto", "USD"]]
    df = load_assets(FakeAthena(["SUCCEEDED"], rows=rows))
    assert df.to_dict("records") == [
        {"asset": "BTC", "asset_name": "Bitcoin", "asset_class": "crypto", "currency": "USD"}
    ]


@pytest.mark.parametrize(
    "sql, table",
    [
        (PRICES_SQL.format(days=MAX_DAYS), "daily_prices"),
        (VOLATILITY_SQL.format(days=MAX_DAYS), "v_rolling_volatility_30d"),
        (ASSETS_SQL, "dim_asset"),
    ],
)
def test_todas_las_consultas_del_dashboard_son_lecturas_permitidas(sql, table):
    validated = validate_sql(sql, max_limit=ROW_LIMIT)
    assert validated.tables == (table,)
