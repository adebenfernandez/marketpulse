"""Las reglas de calidad de MarketPulse: qué se comprueba en cada tabla silver y gold.

Umbrales de frescura (días máximos desde el último dato, contando desde la ejecución diaria de
las 06:00 UTC). Bolsa y BCE no publican en fin de semana ni en festivos: el peor caso habitual es
Semana Santa (viernes y lunes cerrados): el martes por la mañana el último dato es del jueves,
5 días antes. Cripto cotiza todos los días: con 2 días de margen se tolera un fallo puntual.

Saltos diarios (solo AVISO, no paran el proceso): un cambio mayor que esto respecto al dato anterior
del mismo activo merece que alguien lo mire, pero puede ser real.
"""

import logging
from datetime import date

import pandas as pd

from marketpulse.common.config import Watchlist
from marketpulse.quality import checks
from marketpulse.quality.checks import ERROR, CheckResult
from marketpulse.transform.gold import watchlist_assets
from marketpulse.transform.schemas import GOLD_TABLES, SILVER_TABLES

logger = logging.getLogger(__name__)

MAX_AGE_DAYS = {"crypto": 2, "equity": 5, "fx": 5}
MAX_DAILY_JUMP = {"crypto": 0.5, "equity": 0.25, "fx": 0.10}


def check_silver(frames: dict[str, pd.DataFrame]) -> list[CheckResult]:
    results: list[CheckResult] = []

    fx = frames.get("fx_rates")
    if fx is not None and not fx.empty:
        results += checks.not_null(fx, "fx_rates", SILVER_TABLES["fx_rates"][0].names)
        results.append(checks.unique(fx, "fx_rates", SILVER_TABLES["fx_rates"][1]))
        results.append(checks.in_range(fx, "fx_rates", "rate", min_value=0, min_inclusive=False))

    crypto = frames.get("crypto_prices")
    if crypto is not None and not crypto.empty:
        # `symbol` puede ser nulo en silver: una moneda que ya no está en la watchlist
        cols = [c for c in SILVER_TABLES["crypto_prices"][0].names if c != "symbol"]
        results += checks.not_null(crypto, "crypto_prices", cols)
        results.append(checks.unique(crypto, "crypto_prices", SILVER_TABLES["crypto_prices"][1]))
        results.append(
            checks.in_range(crypto, "crypto_prices", "price", min_value=0, min_inclusive=False)
        )
        for col in ("market_cap", "volume_24h"):
            results.append(checks.in_range(crypto, "crypto_prices", col, min_value=0))

    stocks = frames.get("stock_prices")
    if stocks is not None and not stocks.empty:
        results += checks.not_null(stocks, "stock_prices", SILVER_TABLES["stock_prices"][0].names)
        results.append(checks.unique(stocks, "stock_prices", SILVER_TABLES["stock_prices"][1]))
        for col in ("open", "high", "low", "close"):
            results.append(
                checks.in_range(stocks, "stock_prices", col, min_value=0, min_inclusive=False)
            )
        results.append(checks.in_range(stocks, "stock_prices", "volume", min_value=0))
        # Coherencia OHLC: el máximo es el mayor del día y el mínimo el menor
        h, lo = stocks["high"], stocks["low"]
        results.append(checks.rule(stocks, "stock_prices", "high >= low", h >= lo))
        results.append(
            checks.rule(
                stocks, "stock_prices", "low <= open <= high", stocks["open"].between(lo, h)
            )
        )
        results.append(
            checks.rule(
                stocks, "stock_prices", "low <= close <= high", stocks["close"].between(lo, h)
            )
        )
    return results


def check_gold(df: pd.DataFrame, watchlist: Watchlist, today: date) -> list[CheckResult]:
    schema, key = GOLD_TABLES["daily_prices"]
    t = "daily_prices"
    results: list[CheckResult] = []
    results += checks.not_null(df, t, schema.names)
    results.append(checks.unique(df, t, key))
    results.append(checks.in_range(df, t, "price", min_value=0, min_inclusive=False))
    results.append(checks.accepted_values(df, t, "asset_class", set(MAX_AGE_DAYS)))
    results.append(
        checks.accepted_values(df, t, "price_type", {"close", "snapshot", "reference_rate"})
    )

    # Frescura: CADA activo de la watchlist debe tener un dato reciente (según su clase)
    expected = {asset: MAX_AGE_DAYS[cls] for asset, cls in watchlist_assets(watchlist).items()}
    results += checks.freshness(df, t, expected, today)

    # Saltos sospechosos, con un umbral distinto por clase de activo (solo aviso)
    for cls, jump in MAX_DAILY_JUMP.items():
        subset = df[df["asset_class"] == cls]
        if not subset.empty:
            results.append(checks.max_daily_jump(subset, f"{t}[{cls}]", jump))
    return results


def check_dim_asset(dim: pd.DataFrame, facts: pd.DataFrame) -> list[CheckResult]:
    """La dimensión de activos, y que los hechos solo usen activos que existen en ella."""
    schema, key = GOLD_TABLES["dim_asset"]
    t = "dim_asset"
    results = checks.not_null(dim, t, schema.names)
    results.append(checks.unique(dim, t, key))
    results.append(checks.accepted_values(dim, t, "asset_class", set(MAX_AGE_DAYS)))
    # Integridad referencial del modelo en estrella: todo `asset` de la tabla de hechos debe
    # existir en la dimensión. Si no, al cruzarlas (JOIN) ese activo desaparecería sin avisar
    results.append(
        checks.accepted_values(facts, "daily_prices->dim_asset", "asset", set(dim["asset"]))
    )
    return results


def has_errors(results: list[CheckResult]) -> bool:
    return any(not r.passed and r.severity == ERROR for r in results)


def log_report(results: list[CheckResult]) -> None:
    """Escribe en el log un resumen y el detalle de lo que ha fallado."""
    failed = [r for r in results if not r.passed]
    logger.info("Calidad: %d comprobaciones, %d fallan", len(results), len(failed))
    for r in failed:
        log = logger.error if r.severity == ERROR else logger.warning
        log("Calidad %s %s · %s: %d fila(s). Ej.: %s", r.severity.upper(), r.table, r.check,
            r.failed, r.examples)  # fmt: skip
