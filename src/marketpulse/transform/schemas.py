"""Esquemas de las tablas silver: nombre y tipo EXACTO de cada columna.

El esquema es el contrato de la tabla: quien la lea (gold, las comprobaciones de calidad, Athena
en la Fase 4) puede confiar en que `close` es un número y `date` una fecha, no un texto.
Escribir el Parquet con estos esquemas hace que un tipo inesperado falle al escribir, no después.
"""

import pyarrow as pa

# Fechas de calendario (sin hora): pa.date32() · Instantes: timestamp en UTC
UTC_TIMESTAMP = pa.timestamp("us", tz="UTC")  # precisión de microsegundos, zona UTC explícita

FX_RATES = pa.schema(
    [
        ("date", pa.date32()),  # día al que se refiere el tipo (fecha del dato, del BCE)
        ("base", pa.string()),  # EUR
        ("quote", pa.string()),  # USD, GBP...
        ("rate", pa.float64()),  # unidades de `quote` por 1 unidad de `base`
        ("ingest_date", pa.date32()),  # dt de la partición bronze de la que salió (linaje)
    ]
)

CRYPTO_PRICES = pa.schema(
    [
        ("date", pa.date32()),  # día (UTC) de `price_at`
        ("coin_id", pa.string()),  # id de CoinGecko: bitcoin
        ("symbol", pa.string()),  # BTC (de la watchlist)
        ("vs_currency", pa.string()),  # usd
        ("price", pa.float64()),
        ("market_cap", pa.float64()),
        ("volume_24h", pa.float64()),
        ("change_24h_pct", pa.float64()),  # variación en % de las últimas 24 h
        ("price_at", UTC_TIMESTAMP),  # instante exacto del precio (last_updated_at)
        ("ingest_date", pa.date32()),
    ]
)

STOCK_PRICES = pa.schema(
    [
        ("date", pa.date32()),  # sesión de bolsa (fecha de Nueva York, ver silver.py)
        ("symbol", pa.string()),
        ("open", pa.float64()),
        ("high", pa.float64()),
        ("low", pa.float64()),
        ("close", pa.float64()),
        ("volume", pa.int64()),  # nº de acciones negociadas: entero
        ("ingest_date", pa.date32()),
    ]
)

# Nombre de la tabla -> (esquema, columnas que identifican una fila única)
SILVER_TABLES: dict[str, tuple[pa.Schema, list[str]]] = {
    "fx_rates": (FX_RATES, ["date", "base", "quote"]),
    "crypto_prices": (CRYPTO_PRICES, ["date", "coin_id", "vs_currency"]),
    "stock_prices": (STOCK_PRICES, ["date", "symbol"]),
}

# --- Gold -------------------------------------------------------------------------------------
# Una sola tabla "larga": una fila por (día, activo), con las tres clases de activo juntas.
DAILY_PRICES = pa.schema(
    [
        ("date", pa.date32()),  # fecha del dato
        ("asset", pa.string()),  # BTC, SPY, EUR/USD...
        ("asset_class", pa.string()),  # crypto | equity | fx
        ("price", pa.float64()),  # el precio del día (qué precio exactamente: price_type)
        ("currency", pa.string()),  # moneda en la que está expresado `price` (USD, GBP...)
        ("price_type", pa.string()),  # close | snapshot | reference_rate
        ("source", pa.string()),  # alphavantage | coingecko | frankfurter
    ]
)
# Dimensión de activos (modelo en estrella, Fase 4): UNA fila por activo con sus atributos
# descriptivos. Sale de la watchlist, no de los datos: es "lo que sabemos de cada activo".
DIM_ASSET = pa.schema(
    [
        ("asset", pa.string()),  # clave: la misma que en daily_prices (BTC, SPY, EUR/USD)
        ("asset_name", pa.string()),  # nombre legible (Bitcoin, SPDR S&P 500 ETF...)
        ("asset_class", pa.string()),  # crypto | equity | fx
        ("currency", pa.string()),  # moneda en la que se expresa su precio
        ("price_type", pa.string()),  # close | snapshot | reference_rate
        ("source", pa.string()),  # API de la que viene
        ("annualization_days", pa.int32()),  # sesiones al año: 365 cripto, 252 bolsa y divisas
    ]
)
GOLD_TABLES: dict[str, tuple[pa.Schema, list[str]]] = {
    "daily_prices": (DAILY_PRICES, ["date", "asset"]),
    "dim_asset": (DIM_ASSET, ["asset"]),
}
