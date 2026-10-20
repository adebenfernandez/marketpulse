"""Silver -> gold: una tabla diaria por activo, igual para divisas, cripto y acciones.

Gold es la capa "lista para consumir": la que leerán Athena (Fase 4), el agente (Fase 7) y el
dashboard. Por eso prima que sea fácil de entender y difícil de malinterpretar:
- Formato LARGO: una fila por (date, asset). Añadir un activo nuevo es añadir filas, no columnas.
- Cada fila dice en qué moneda está el precio (`currency`) y qué tipo de precio es (`price_type`),
  porque un cierre de bolsa, una foto de cripto y un tipo de referencia del BCE no son lo mismo.
- Sin columna de volumen: el de las acciones son ACCIONES negociadas y el de cripto son DÓLARES
  en 24 h. Mezclar unidades en una columna invita a sumar peras con manzanas. Sigue en silver.
"""

import logging
from pathlib import Path

import pandas as pd

from marketpulse.common.config import Watchlist
from marketpulse.common.storage import DEFAULT_DATA_ROOT
from marketpulse.transform.schemas import GOLD_TABLES
from marketpulse.transform.tables import read_table, write_table

logger = logging.getLogger(__name__)

# Supuesto documentado: los símbolos de Alpha Vantage de la watchlist cotizan en EE. UU., en USD
EQUITY_CURRENCY = "USD"


def equity_daily(stocks: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": stocks["date"],
            "asset": stocks["symbol"],
            "asset_class": "equity",
            "price": stocks["close"],  # precio de cierre de la sesión
            "currency": EQUITY_CURRENCY,
            "price_type": "close",
            "source": "alphavantage",
        }
    )


def crypto_daily(crypto: pd.DataFrame, vs_currency: str) -> pd.DataFrame:
    # Solo la moneda de la watchlist: si algún día hubiera precios en varias monedas,
    # (date, asset) dejaría de ser único
    crypto = crypto[crypto["vs_currency"] == vs_currency]
    return pd.DataFrame(
        {
            "date": crypto["date"],
            "asset": crypto["symbol"],
            "asset_class": "crypto",
            "price": crypto["price"],  # foto del precio en el momento de la ingesta
            "currency": crypto["vs_currency"].str.upper(),  # usd -> USD, como las demás
            "price_type": "snapshot",
            "source": "coingecko",
        }
    )


def fx_daily(fx: pd.DataFrame) -> pd.DataFrame:
    # EUR/USD = 1,12 significa "1 EUR vale 1,12 USD": el precio del EUR expresado en USD.
    # Por eso la moneda del precio es la `quote`, no la `base`.
    return pd.DataFrame(
        {
            "date": fx["date"],
            "asset": fx["base"] + "/" + fx["quote"],
            "asset_class": "fx",
            "price": fx["rate"],
            "currency": fx["quote"],
            "price_type": "reference_rate",
            "source": "frankfurter",
        }
    )


def watchlist_assets(watchlist: Watchlist) -> dict[str, str]:
    """Los activos que seguimos HOY según la watchlist: {asset (como en gold): asset_class}.

    Es la ÚNICA definición de "qué activos se publican": la usan gold y las comprobaciones de
    calidad (quality/rules.py), para que nunca puedan discrepar.
    """
    assets = {a.symbol: "crypto" for a in watchlist.crypto.assets}
    assets |= {a.symbol: "equity" for a in watchlist.stocks.assets}
    assets |= {f"{watchlist.fx.base}/{q}": "fx" for q in watchlist.fx.quotes}
    return assets


def daily_prices_from(silver: dict[str, pd.DataFrame], watchlist: Watchlist) -> pd.DataFrame:
    """Une las tablas silver (ya en memoria) en la tabla gold `daily_prices`.

    Gold contiene SOLO los activos de la watchlist actual: si se quita un activo, su historia
    sigue en bronze y silver, pero deja de publicarse. Así "gold" = "lo que seguimos hoy".
    """
    parts = []
    # Cada tabla silver es opcional: si una fuente aún no tiene datos, gold sale sin ella
    if not silver.get("stock_prices", pd.DataFrame()).empty:
        parts.append(equity_daily(silver["stock_prices"]))
    if not silver.get("crypto_prices", pd.DataFrame()).empty:
        parts.append(crypto_daily(silver["crypto_prices"], watchlist.crypto.vs_currency))
    if not silver.get("fx_rates", pd.DataFrame()).empty:
        parts.append(fx_daily(silver["fx_rates"]))

    schema, key = GOLD_TABLES["daily_prices"]
    if not parts:
        return pd.DataFrame(columns=schema.names)
    df = pd.concat(parts, ignore_index=True)

    tracked = df["asset"].isin(watchlist_assets(watchlist))
    if not tracked.all():
        dropped = sorted(df.loc[~tracked, "asset"].astype(str).unique())
        logger.info("Gold: se omiten activos que ya no están en la watchlist: %s", dropped)
    return df[tracked].sort_values(key).reset_index(drop=True)


def load_silver(root: Path = DEFAULT_DATA_ROOT) -> dict[str, pd.DataFrame]:
    """Lee del disco las tablas silver que existan."""
    silver = root / "silver"
    return {
        name: read_table(silver / name)
        for name in ("stock_prices", "crypto_prices", "fx_rates")
        if (silver / name).exists()
    }


def build_daily_prices(watchlist: Watchlist, root: Path = DEFAULT_DATA_ROOT) -> pd.DataFrame:
    """Lee silver del disco y construye `daily_prices` (sin escribirla)."""
    return daily_prices_from(load_silver(root), watchlist)


def build_gold(watchlist: Watchlist, root: Path = DEFAULT_DATA_ROOT) -> dict[str, Path]:
    """Construye y escribe las tablas gold desde el silver del disco (sin comprobaciones)."""
    return write_gold(build_daily_prices(watchlist, root), root)


def write_gold(df: pd.DataFrame, root: Path = DEFAULT_DATA_ROOT) -> dict[str, Path]:
    """Escribe `daily_prices` ya construida. Devuelve {tabla: carpeta escrita}."""
    if df.empty:
        logger.warning("Gold daily_prices: no hay datos en silver, no se escribe")
        return {}
    schema, _ = GOLD_TABLES["daily_prices"]
    path = write_table(df, schema, root / "gold" / "daily_prices")
    counts = df["asset_class"].value_counts().to_dict()
    logger.info("Gold daily_prices: %d filas %s en %s", len(df), counts, path)
    return {"daily_prices": path}
