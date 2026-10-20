"""Cliente de CoinGecko: precio, capitalización, volumen y variación 24 h de las criptomonedas.

Documentación: https://docs.coingecko.com/ (endpoint /simple/price).
- Sin clave ("keyless"): límite por IP compartido con todos los que usan esa IP. En Lambda
  (Fase 3) las IP de AWS son compartidas, así que conviene la clave Demo gratuita.
- Con clave Demo: 100 llamadas/min y 10.000/mes; se envía en la cabecera `x-cg-demo-api-key`
  (no en la URL, para que no aparezca en logs). Hacemos 1 llamada al día.
- Condiciones: el plan gratuito exige atribución ("datos de CoinGecko") donde se muestren.

Respuesta (un diccionario por id; `last_updated_at` en segundos UNIX, UTC):
    {"bitcoin": {"usd": 82388, "usd_market_cap": ..., "usd_24h_vol": ...,
                 "usd_24h_change": -1.4, "last_updated_at": 1792509891}, ...}
"""

import logging
from datetime import date
from pathlib import Path

from marketpulse.common.config import CryptoConfig
from marketpulse.common.http import HttpClient
from marketpulse.common.storage import DEFAULT_DATA_ROOT, write_bronze
from marketpulse.ingest.errors import UnexpectedResponseError

logger = logging.getLogger(__name__)

SOURCE = "coingecko"
PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
API_KEY_HEADER = "x-cg-demo-api-key"
API_KEY_ENV = "COINGECKO_API_KEY"  # nombre de la variable en .env (local) o en Lambda


def fetch_prices(client: HttpClient, crypto: CryptoConfig, api_key: str | None = None) -> dict:
    """Pide en una sola llamada el precio de todas las criptomonedas de la watchlist."""
    vs = crypto.vs_currency
    params = {
        "ids": ",".join(a.coingecko_id for a in crypto.assets),  # "bitcoin,ethereum,solana"
        "vs_currencies": vs,
        "include_market_cap": "true",
        "include_24hr_vol": "true",
        "include_24hr_change": "true",
        "include_last_updated_at": "true",  # para saber de cuándo es cada precio
    }
    # La clave es opcional: sin ella funciona, pero con límites más estrictos (ver docstring)
    headers = {API_KEY_HEADER: api_key} if api_key else None
    if not api_key:
        logger.info("CoinGecko sin clave (%s no definida): se usa el acceso público", API_KEY_ENV)

    data = client.get_json(PRICE_URL, params=params, headers=headers)

    if not isinstance(data, dict) or not data:
        raise UnexpectedResponseError(
            f"CoinGecko: se esperaba un diccionario no vacío: {data!r:.200}"
        )
    for coin_id, values in data.items():
        if not isinstance(values, dict) or vs not in values:
            raise UnexpectedResponseError(
                f"CoinGecko: '{coin_id}' sin precio en {vs}: {values!r:.200}"
            )

    # Un id mal escrito en la watchlist no da error en CoinGecko: simplemente no aparece
    missing = {a.coingecko_id for a in crypto.assets} - data.keys()
    if missing:
        logger.warning("CoinGecko no devolvió estos ids (¿mal escritos?): %s", sorted(missing))
    return data


def ingest(
    client: HttpClient,
    crypto: CryptoConfig,
    api_key: str | None = None,
    dt: date | None = None,
    root: Path = DEFAULT_DATA_ROOT,
) -> Path:
    """Descarga los precios y los guarda en bronze. Devuelve la ruta del fichero escrito."""
    data = fetch_prices(client, crypto, api_key)
    path = write_bronze(SOURCE, data, dt=dt, root=root)
    logger.info("CoinGecko: %d criptomonedas guardadas en %s", len(data), path)
    return path
