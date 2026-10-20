"""Bronze -> silver: de las respuestas originales de cada API a tablas limpias y tipadas.

Qué hace la capa silver con cada fuente:
- Nombres en snake_case y en inglés, iguales para todas las fuentes (`date`, `symbol`, `close`...).
- Tipos correctos: los precios de Alpha Vantage llegan como TEXTO ("582.40") y pasan a número.
- Tiempo: los instantes pasan a UTC (`last_updated_at` de CoinGecko, en segundos UNIX). Las
  fechas sin hora se dejan como fecha de calendario (ver `stock_rows`).
- Sin duplicados: la misma fila aparece en varias ejecuciones (Alpha Vantage repite 100 días cada
  día; el BCE no publica en fin de semana). Se queda la versión más reciente.
"""

import logging
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from marketpulse.common.config import Watchlist
from marketpulse.common.storage import DEFAULT_DATA_ROOT
from marketpulse.transform.bronze import iter_bronze
from marketpulse.transform.schemas import SILVER_TABLES
from marketpulse.transform.tables import write_table

logger = logging.getLogger(__name__)


# --- 1) Una función por fuente: JSON de bronze -> lista de filas (diccionarios) -------------


def fx_rows(payload: list[dict], ingest_date: date) -> list[dict]:
    """Frankfurter ya viene "en filas": solo renombramos y convertimos tipos."""
    return [
        {
            "date": date.fromisoformat(r["date"]),
            "base": r["base"],
            "quote": r["quote"],
            "rate": float(r["rate"]),
            "ingest_date": ingest_date,
        }
        for r in payload
    ]


def crypto_rows(payload: dict, ingest_date: date, symbols: dict[str, str]) -> list[dict]:
    """CoinGecko viene como {id: {usd: ..., usd_market_cap: ...}}: lo "aplanamos" a filas.

    `symbols` traduce el id de CoinGecko al símbolo (bitcoin -> BTC) usando la watchlist.
    """
    rows = []
    for coin_id, values in payload.items():
        # La moneda (usd) es la única clave que no lleva prefijo ni es un campo conocido
        vs = next(k for k in values if "_" not in k)
        # last_updated_at: segundos desde 1970 en UTC -> instante con zona horaria explícita
        price_at = datetime.fromtimestamp(values["last_updated_at"], tz=UTC)
        rows.append(
            {
                "date": price_at.date(),  # día UTC del precio
                "coin_id": coin_id,
                "symbol": symbols.get(coin_id),  # None si ya no está en la watchlist
                "vs_currency": vs,
                "price": float(values[vs]),
                "market_cap": float(values[f"{vs}_market_cap"]),
                "volume_24h": float(values[f"{vs}_24h_vol"]),
                "change_24h_pct": float(values[f"{vs}_24h_change"]),
                "price_at": price_at,
                "ingest_date": ingest_date,
            }
        )
    return rows


def stock_rows(payload: dict, ingest_date: date) -> list[dict]:
    """Alpha Vantage: una fila por día de la serie, con los precios pasados de texto a número.

    Sobre la zona horaria: la API dice "US/Eastern", pero la serie diaria solo trae FECHAS de
    sesión ("2026-10-19"), sin hora. Una fecha de sesión es un día de calendario, no un instante:
    convertirla a UTC no tiene sentido (la sesión del 19 en Nueva York es "el 19"): se deja igual.
    """
    symbol = payload["Meta Data"]["2. Symbol"]
    return [
        {
            "date": date.fromisoformat(day),
            "symbol": symbol,
            "open": float(v["1. open"]),
            "high": float(v["2. high"]),
            "low": float(v["3. low"]),
            "close": float(v["4. close"]),
            "volume": int(v["5. volume"]),
            "ingest_date": ingest_date,
        }
        for day, v in payload["Time Series (Daily)"].items()
    ]


# --- 2) Juntar todas las ejecuciones y quitar duplicados ------------------------------------


def deduplicate(df: pd.DataFrame, key: list[str], order_by: list[str]) -> pd.DataFrame:
    """Deja una fila por `key`: la última según `order_by` (la descarga más reciente gana)."""
    before = len(df)
    df = (
        df.sort_values(order_by, kind="stable")  # stable: ante empates, respeta el orden previo
        .drop_duplicates(subset=key, keep="last")
        .sort_values(key)
        .reset_index(drop=True)
    )
    logger.info("Deduplicado: %d filas -> %d (clave %s)", before, len(df), key)
    return df


def build_fx_rates(root: Path) -> pd.DataFrame:
    rows = [
        row for f in iter_bronze("frankfurter", root) for row in fx_rows(f.payload, f.ingest_date)
    ]
    df = pd.DataFrame(rows, columns=SILVER_TABLES["fx_rates"][0].names)
    return deduplicate(df, SILVER_TABLES["fx_rates"][1], ["ingest_date"])


def build_crypto_prices(root: Path, watchlist: Watchlist) -> pd.DataFrame:
    symbols = {a.coingecko_id: a.symbol for a in watchlist.crypto.assets}
    rows = [
        row
        for f in iter_bronze("coingecko", root)
        for row in crypto_rows(f.payload, f.ingest_date, symbols)
    ]
    df = pd.DataFrame(rows, columns=SILVER_TABLES["crypto_prices"][0].names)
    # Si hay dos precios del mismo día (dos ejecuciones), nos quedamos con el más tardío
    return deduplicate(df, SILVER_TABLES["crypto_prices"][1], ["price_at", "ingest_date"])


def build_stock_prices(root: Path) -> pd.DataFrame:
    rows = [
        row
        for f in iter_bronze("alphavantage", root)
        for row in stock_rows(f.payload, f.ingest_date)
    ]
    df = pd.DataFrame(rows, columns=SILVER_TABLES["stock_prices"][0].names)
    # Cada día llegan otra vez los últimos 100 días: si un dato se corrigió, gana el más reciente
    return deduplicate(df, SILVER_TABLES["stock_prices"][1], ["ingest_date"])


# --- 3) Construir y guardar las tres tablas --------------------------------------------------


def build_silver_frames(
    watchlist: Watchlist, root: Path = DEFAULT_DATA_ROOT
) -> dict[str, pd.DataFrame]:
    """Construye las tablas silver EN MEMORIA, sin escribir nada (para poder comprobarlas antes)."""
    return {
        "fx_rates": build_fx_rates(root),
        "crypto_prices": build_crypto_prices(root, watchlist),
        "stock_prices": build_stock_prices(root),
    }


def build_silver(watchlist: Watchlist, root: Path = DEFAULT_DATA_ROOT) -> dict[str, Path]:
    """Reconstruye y escribe las tablas silver desde todo bronze (sin comprobaciones)."""
    return write_silver(build_silver_frames(watchlist, root), root)


def write_silver(
    frames: dict[str, pd.DataFrame], root: Path = DEFAULT_DATA_ROOT
) -> dict[str, Path]:
    """Escribe las tablas silver ya construidas. Devuelve {tabla: carpeta escrita}."""
    written = {}
    for name, df in frames.items():
        if df.empty:
            # Sin datos no hay tabla que escribir (p. ej. una fuente que aún no se ha descargado)
            logger.warning("Silver %s: no hay datos en bronze, no se escribe", name)
            continue
        schema = SILVER_TABLES[name][0]
        written[name] = write_table(df, schema, root / "silver" / name)
        logger.info("Silver %s: %d filas en %s", name, len(df), written[name])
    return written
