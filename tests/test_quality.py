"""Tests de calidad: cada comprobación pasa con datos buenos y FALLA con un dato erróneo.

Esto cubre el criterio de aceptación de la Fase 2: "las comprobaciones de calidad pasan, y fallan
cuando se introduce un dato erróneo a propósito en un test".
"""

from datetime import date

import pandas as pd
import pytest

from marketpulse.common.config import parse_watchlist
from marketpulse.common.storage import write_bronze
from marketpulse.quality import checks, rules
from marketpulse.quality.checks import ERROR, WARNING
from marketpulse.transform import run
from marketpulse.transform.gold import daily_prices_from
from marketpulse.transform.silver import build_silver_frames
from marketpulse.transform.tables import read_table

D19, D20 = date(2026, 10, 19), date(2026, 10, 20)

# Watchlist mínima para los tests: un activo de cada clase
WATCHLIST = parse_watchlist(
    {
        "fx": {"base": "EUR", "quotes": ["USD"]},
        "crypto": {"vs_currency": "usd", "assets": [{"symbol": "BTC", "coingecko_id": "bitcoin"}]},
        "stocks": {"assets": [{"symbol": "SPY"}]},
    }
)


def gold_row(asset="SPY", day=D20, price=766.48, asset_class="equity", **extra) -> dict:
    row = {
        "date": day,
        "asset": asset,
        "asset_class": asset_class,
        "price": price,
        "currency": "USD",
        "price_type": "close",
        "source": "alphavantage",
    }
    return row | extra


# --- Comprobaciones genéricas: pasa / falla ------------------------------------------------


def test_not_null():
    df = pd.DataFrame([gold_row(), gold_row(day=D19, price=None)])
    (ok,) = checks.not_null(df, "t", ["asset"])
    (bad,) = checks.not_null(df, "t", ["price"])
    assert ok.passed
    assert not bad.passed and bad.failed == 1 and bad.severity == ERROR


def test_unique_marca_todas_las_filas_repetidas():
    df = pd.DataFrame([gold_row(), gold_row(price=767.0), gold_row(day=D19)])
    result = checks.unique(df, "t", ["date", "asset"])
    assert result.failed == 2  # las dos versiones del mismo (día, activo)


@pytest.mark.parametrize(("price", "passed"), [(766.48, True), (0.0, False), (-5.0, False)])
def test_precio_debe_ser_positivo(price, passed):
    df = pd.DataFrame([gold_row(price=price)])
    assert checks.in_range(df, "t", "price", min_value=0, min_inclusive=False).passed is passed


def test_accepted_values():
    df = pd.DataFrame([gold_row(), gold_row(day=D19, asset_class="bonos")])
    assert checks.accepted_values(df, "t", "asset_class", {"equity", "crypto", "fx"}).failed == 1


def test_freshness_detecta_datos_viejos_y_activos_sin_datos():
    df = pd.DataFrame([gold_row(day=D20), gold_row(asset="BTC", day=date(2026, 10, 10))])
    results = checks.freshness(df, "t", {"SPY": 5, "BTC": 2, "ADA": 2}, today=D20)
    by_check = {r.check: r.passed for r in results}
    assert by_check == {
        "freshness(ADA)": False,  # está en la watchlist pero nunca se ha descargado
        "freshness(BTC)": False,  # último dato hace 10 días
        "freshness(SPY)": True,
    }


def test_salto_diario_es_aviso_no_error():
    df = pd.DataFrame([gold_row(day=D19, price=100.0), gold_row(day=D20, price=180.0)])
    result = checks.max_daily_jump(df, "t", max_jump=0.25)
    assert result.failed == 1 and result.severity == WARNING


def test_sin_saltos_no_hay_falsos_positivos():
    # Regresión: con 0 saltos, pandas fabricaba filas NaN y la regla "fallaba" en todas
    df = pd.DataFrame([gold_row(day=D19, price=100.0), gold_row(day=D20, price=101.0)])
    result = checks.max_daily_jump(df, "t", max_jump=0.25)
    assert result.passed and result.examples == []


def test_has_errors_ignora_los_avisos():
    aviso = checks.CheckResult("t", "x", WARNING, failed=3)
    error = checks.CheckResult("t", "y", ERROR, failed=1)
    assert not rules.has_errors([aviso])
    assert rules.has_errors([aviso, error])


# --- Reglas de MarketPulse sobre silver -------------------------------------------------------


def stocks(**changes) -> pd.DataFrame:
    row = {"date": D20, "symbol": "SPY", "open": 760.0, "high": 770.0, "low": 759.0,
           "close": 766.48, "volume": 41_000_000, "ingest_date": D20} | changes  # fmt: skip
    return pd.DataFrame([row])


def failed_checks(frames) -> set[str]:
    return {r.check for r in rules.check_silver(frames) if not r.passed}


def test_silver_bueno_pasa_todo():
    assert failed_checks({"stock_prices": stocks()}) == set()


@pytest.mark.parametrize(
    ("cambio", "regla"),
    [
        ({"high": 750.0}, "rule(high >= low)"),  # máximo por debajo del mínimo
        ({"close": 800.0}, "rule(low <= close <= high)"),  # cierre fuera del rango del día
        ({"open": -1.0}, "range(open > 0)"),
        ({"volume": -10}, "range(volume >= 0)"),
        ({"symbol": None}, "not_null(symbol)"),
    ],
)
def test_silver_con_dato_erroneo_falla(cambio, regla):
    assert regla in failed_checks({"stock_prices": stocks(**cambio)})


# --- De principio a fin: un dato erróneo en bronze impide publicar -------------------------


def write_day(root, close: str):
    """Bronze de un día con las tres fuentes; `close` es el cierre de SPY (texto, como la API)."""
    fx = [{"date": "2026-10-20", "base": "EUR", "quote": "USD", "rate": 1.1215}]
    write_bronze("frankfurter", fx, dt=D20, root=root)
    cg = {"bitcoin": {"usd": 82388.0, "usd_market_cap": 1.6e12, "usd_24h_vol": 2.7e10,
                      "usd_24h_change": 0.5, "last_updated_at": 1792509891}}  # fmt: skip
    write_bronze("coingecko", cg, dt=D20, root=root)
    av = {"Meta Data": {"2. Symbol": "SPY"}, "Time Series (Daily)": {"2026-10-19": {
        "1. open": "760", "2. high": "770", "3. low": "759", "4. close": close,
        "5. volume": "41000000"}}}  # fmt: skip
    write_bronze("alphavantage", av, dt=D20, name="SPY", root=root)


def test_datos_buenos_se_publican(tmp_path):
    write_day(tmp_path, close="766.48")
    assert run.run_transform(WATCHLIST, root=tmp_path, today=D20) is True
    gold = read_table(tmp_path / "gold" / "daily_prices")
    assert sorted(gold["asset"]) == ["BTC", "EUR/USD", "SPY"]


def test_un_dato_erroneo_no_se_publica_y_se_conserva_lo_anterior(tmp_path):
    write_day(tmp_path, close="766.48")
    run.run_transform(WATCHLIST, root=tmp_path, today=D20)  # publicación buena
    antes = read_table(tmp_path / "silver" / "stock_prices")

    write_day(tmp_path, close="-1")  # mismo día, ahora con un cierre negativo a propósito
    assert run.run_transform(WATCHLIST, root=tmp_path, today=D20) is False

    despues = read_table(tmp_path / "silver" / "stock_prices")
    assert despues.equals(antes)  # silver sigue siendo la versión buena
    assert (
        read_table(tmp_path / "gold" / "daily_prices").query("asset == 'SPY'")["price"].iloc[0] > 0
    )


def test_datos_viejos_no_se_publican(tmp_path):
    write_day(tmp_path, close="766.48")
    # Diez días después sin nuevas descargas: la frescura falla
    assert run.run_transform(WATCHLIST, root=tmp_path, today=date(2026, 10, 30)) is False


def test_gold_solo_publica_los_activos_de_la_watchlist(tmp_path):
    write_day(tmp_path, close="766.48")
    sin_spy = parse_watchlist(
        {
            "fx": {"base": "EUR", "quotes": ["USD"]},
            "crypto": {
                "vs_currency": "usd",
                "assets": [{"symbol": "BTC", "coingecko_id": "bitcoin"}],
            },
            "stocks": {"assets": [{"symbol": "VT"}]},
        }
    )
    gold = daily_prices_from(build_silver_frames(sin_spy, tmp_path), sin_spy)
    assert "SPY" not in set(gold["asset"])  # sigue en silver, pero ya no se publica en gold
