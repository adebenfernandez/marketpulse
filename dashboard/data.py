"""Capa de datos del dashboard (paso 8.3, D-040): las consultas a Athena, sin Streamlit.

Separada de la interfaz para poder probarla sin navegador y sin AWS (con un Athena falso).
- Las consultas son FIJAS y las escribimos nosotros. Lo único variable es `days`, que se
  comprueba que sea un entero entre 1 y MAX_DAYS antes de meterlo en la SQL: el usuario nunca
  escribe SQL desde los gráficos (la caja de preguntas va por el agente, con sus barreras).
- Aun así pasan por el mismo validador que el agente (guard.validate_sql): solo SELECT, solo
  tablas de la lista blanca y LIMIT. Si mañana alguien cambia una consulta por error, se para
  aquí y no en Athena.
- Se ejecutan con los clientes que se pasan: en el dashboard, los del rol de solo lectura
  marketpulse-agent (D-033); en los tests, un Athena falso.
Athena devuelve todo como texto: aquí se convierte a fechas y números para los gráficos.
"""

import pandas as pd

from marketpulse.agent.guard import validate_sql
from marketpulse.common.athena import run_query

MAX_DAYS = 365  # el histórico llega a un año (backfill, D-022)
ROW_LIMIT = 5_000  # 8 activos x 365 días = 2.920 filas como mucho; el LIMIT es la red de seguridad

PRICES_SQL = """
SELECT "date", asset, asset_class, price, currency
FROM daily_prices
WHERE "date" >= date_add('day', -{days}, current_date)
ORDER BY asset, "date"
"""

VOLATILITY_SQL = """
SELECT "date", asset, asset_class, annualized_volatility_30
FROM v_rolling_volatility_30d
WHERE "date" >= date_add('day', -{days}, current_date)
ORDER BY asset, "date"
"""

ASSETS_SQL = """
SELECT asset, asset_name, asset_class, currency
FROM dim_asset
ORDER BY asset_class, asset
"""


def load_prices(athena, days: int = 180) -> pd.DataFrame:
    """Precio diario de cada activo en los últimos `days` días (formato largo)."""
    df = _query(athena, PRICES_SQL.format(days=_check_days(days)))
    return _typed(df, dates=["date"], numbers=["price"])


def load_volatility(athena, days: int = 180) -> pd.DataFrame:
    """Volatilidad anualizada a 30 sesiones de cada activo y día (v_rolling_volatility_30d)."""
    df = _query(athena, VOLATILITY_SQL.format(days=_check_days(days)))
    return _typed(df, dates=["date"], numbers=["annualized_volatility_30"])


def load_assets(athena) -> pd.DataFrame:
    """Los activos de la watchlist con su nombre, para las etiquetas y los filtros."""
    return _query(athena, ASSETS_SQL)


def latest_volatility(volatility: pd.DataFrame) -> pd.DataFrame:
    """La última volatilidad de CADA activo, de mayor a menor.

    No vale filtrar por la fecha máxima de toda la tabla: la bolsa no tiene el cierre de hoy
    cuando cripto y divisas sí, y se quedaría fuera (el error que encontró el paso 7.6).
    """
    if volatility.empty:
        return volatility
    last = volatility.sort_values("date").groupby("asset", as_index=False).tail(1)
    return last.sort_values("annualized_volatility_30", ascending=False).reset_index(drop=True)


def rebase_to_100(prices: pd.DataFrame) -> pd.DataFrame:
    """Añade `index_100`: el precio de cada activo dividido por su PRIMER precio del periodo, x100.

    BTC vale ~84.000 USD y EUR/GBP ~0,87: en un mismo gráfico, la divisa sería una línea plana.
    Con base 100, todos empiezan en 100 y se compara cuánto ha subido o bajado cada uno
    (110 = +10 %).
    """
    if prices.empty:
        return prices.assign(index_100=pd.Series(dtype="float64"))
    ordered = prices.sort_values(["asset", "date"])
    first = ordered.groupby("asset")["price"].transform("first")
    return ordered.assign(index_100=ordered["price"] / first * 100).reset_index(drop=True)


def asset_summary(
    prices: pd.DataFrame, window_days: int = 30, spark_points: int = 30
) -> pd.DataFrame:
    """Una fila por activo para las tarjetas: último precio, variación y mini-serie.

    - `change_pct`: del primer precio de los últimos `window_days` días NATURALES (contados
      desde el último dato de ESE activo) al último. Así la bolsa, que no cotiza el fin de
      semana, se compara sobre el mismo periodo que la cripto.
    - `spark`: los últimos `spark_points` precios, para el mini-gráfico.
    """
    columns = ["asset", "asset_class", "currency", "last_date", "last_price", "change_pct", "spark"]
    if prices.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for asset, group in prices.sort_values("date").groupby("asset", sort=False):
        last = group.iloc[-1]
        window = group[group["date"] >= last["date"] - pd.Timedelta(days=window_days)]
        first_price = window["price"].iloc[0]
        rows.append(
            {
                "asset": asset,
                "asset_class": last["asset_class"],
                "currency": last["currency"],
                "last_date": last["date"],
                "last_price": last["price"],
                "change_pct": (last["price"] / first_price - 1) * 100,
                "spark": group["price"].tail(spark_points).tolist(),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def _check_days(days: int) -> int:
    # bool es un int en Python (True == 1): se rechaza aparte para no aceptar days=True
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= MAX_DAYS:
        raise ValueError(f"days debe ser un entero entre 1 y {MAX_DAYS}, no {days!r}")
    return days


def _query(athena, sql: str) -> pd.DataFrame:
    validated = validate_sql(sql, max_limit=ROW_LIMIT)  # lanza SqlRejectedError si no es lectura
    result = run_query(athena, validated.sql)
    return pd.DataFrame(result.rows, columns=result.columns)


def _typed(df: pd.DataFrame, dates: list[str], numbers: list[str]) -> pd.DataFrame:
    for col in dates:
        df[col] = pd.to_datetime(df[col])
    for col in numbers:
        # Sin errors="coerce": un valor raro debe fallar, no convertirse en NaN sin avisar
        df[col] = pd.to_numeric(df[col])
    return df
