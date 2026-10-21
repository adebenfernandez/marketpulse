"""Carga histórica única (backfill): un año de tipos del BCE y de precios cripto.

La ingesta diaria solo trae "lo de hoy", así que cripto y divisas tenían 1 o 2 días de historia:
pocos para calcular volatilidades de 30 días o correlaciones (Fase 4). Este módulo se ejecuta A
MANO, una vez (o de nuevo si hiciera falta: es idempotente):

    python -m marketpulse.ingest.backfill

Qué hace:
  1. Frankfurter: todos los tipos del BCE del último año en UNA petición (from/to). La respuesta
     tiene la misma forma que la diaria: silver la lee igual.
  2. CoinGecko: 365 días de precio, capitalización y volumen por moneda (/market_chart), el
     máximo del plan Demo. Un punto diario a las 00:00 UTC.
  3. Lo guarda en bronze en fuentes PROPIAS (source=frankfurter_backfill, coingecko_backfill),
     separadas de la ingesta diaria: se ve de dónde viene cada dato y se puede rehacer sin tocar
     lo demás.
  4. Sube a S3 SOLO esas dos carpetas (nunca el resto de data/, que puede estar desactualizado).
Alpha Vantage no se incluye: más de 100 días (outputsize=full) es de pago.
"""

import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from marketpulse.common.config import DEFAULT_WATCHLIST_PATH, CryptoConfig, FxConfig, Watchlist
from marketpulse.common.http import HttpClient
from marketpulse.common.storage import DEFAULT_DATA_ROOT, utc_today, write_bronze
from marketpulse.ingest import coingecko, frankfurter
from marketpulse.ingest.errors import UnexpectedResponseError

logger = logging.getLogger("marketpulse.ingest.backfill")  # nombre fijo, como en common/s3.py

FX_SOURCE = "frankfurter_backfill"
CRYPTO_SOURCE = "coingecko_backfill"
HISTORY_DAYS = 365  # máximo de historia del plan Demo de CoinGecko
MARKET_CHART_URL = "https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"


def fetch_fx_history(client: HttpClient, fx: FxConfig, start: date, end: date) -> list[dict]:
    """Tipos del BCE entre `start` y `end` (ambos incluidos) en una sola petición."""
    params = {
        "base": fx.base,
        "quotes": ",".join(fx.quotes),
        "providers": frankfurter.PROVIDER,
        "from": start.isoformat(),
        "to": end.isoformat(),
    }
    data = client.get_json(frankfurter.RATES_URL, params=params)
    frankfurter.validate_rates(data, fx)  # misma forma que la diaria: misma comprobación
    return data


def fetch_crypto_history(
    client: HttpClient, coin_id: str, vs_currency: str, api_key: str | None
) -> dict:
    """{"prices": [[ms, precio], ...], "market_caps": [...], "total_volumes": [...]}."""
    params = {"vs_currency": vs_currency, "days": str(HISTORY_DAYS), "interval": "daily"}
    headers = {coingecko.API_KEY_HEADER: api_key} if api_key else None
    data = client.get_json(MARKET_CHART_URL.format(coin_id=coin_id), params=params, headers=headers)

    series = ("prices", "market_caps", "total_volumes")
    if not isinstance(data, dict) or any(not data.get(s) for s in series):
        raise UnexpectedResponseError(
            f"CoinGecko market_chart de {coin_id}: faltan series en {data!r:.200}"
        )
    return data


def run_backfill(
    client: HttpClient,
    watchlist: Watchlist,
    api_key: str | None,
    dt: date | None = None,
    root: Path = DEFAULT_DATA_ROOT,
) -> list[Path]:
    """Descarga la historia y la guarda en bronze. Devuelve las rutas escritas."""
    dt = dt or utc_today()
    paths = []

    fx_data = fetch_fx_history(client, watchlist.fx, dt - timedelta(days=HISTORY_DAYS), dt)
    paths.append(write_bronze(FX_SOURCE, fx_data, dt=dt, name="frankfurter", root=root))
    logger.info("Backfill Frankfurter: %d tipos (%d días)", len(fx_data), len(fx_data) // 2)

    crypto: CryptoConfig = watchlist.crypto
    for asset in crypto.assets:
        data = fetch_crypto_history(client, asset.coingecko_id, crypto.vs_currency, api_key)
        # Un fichero por moneda, con el id de CoinGecko como nombre: silver lo usa como coin_id
        paths.append(write_bronze(CRYPTO_SOURCE, data, dt=dt, name=asset.coingecko_id, root=root))
        logger.info("Backfill CoinGecko %s: %d puntos", asset.coingecko_id, len(data["prices"]))
    return paths


def main() -> int:
    import boto3
    from dotenv import load_dotenv

    from marketpulse.common.config import load_watchlist
    from marketpulse.common.s3 import BUCKET_ENV, upload_layers
    from marketpulse.ingest.run import LOG_FORMAT, get_secret

    load_dotenv()
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper(), format=LOG_FORMAT)
    bucket = get_secret(os.environ, BUCKET_ENV)
    if not bucket:
        logger.error("Falta la variable %s (nombre del bucket, ver .env.example)", BUCKET_ENV)
        return 1

    watchlist = load_watchlist(os.environ.get("MARKETPULSE_WATCHLIST", DEFAULT_WATCHLIST_PATH))
    api_key = get_secret(os.environ, coingecko.API_KEY_ENV)
    run_backfill(HttpClient(), watchlist, api_key)

    # Solo las dos carpetas del backfill: upload_layers admite subcarpetas como "capa"
    s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "eu-north-1"))
    upload_layers(
        s3,
        bucket,
        root=DEFAULT_DATA_ROOT,
        layers=(f"bronze/source={FX_SOURCE}", f"bronze/source={CRYPTO_SOURCE}"),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
