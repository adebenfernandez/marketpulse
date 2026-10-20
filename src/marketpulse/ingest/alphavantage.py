"""Cliente de Alpha Vantage: serie diaria de acciones y ETF (apertura, máx., mín., cierre, volumen).

Documentación: https://www.alphavantage.co/documentation/ (función TIME_SERIES_DAILY).
- Clave OBLIGATORIA (gratuita). Plan gratuito: 25 peticiones al día. Hacemos 1 por símbolo.
- `outputsize=compact` (últimos 100 días) es lo que permite el plan gratuito; `full` es de pago.
  Pedir 100 días cada día es redundante, pero no cuesta más (sigue siendo 1 petición) y
  rellena huecos si algún día falla la ingesta.
- La clave va en la URL (`apikey=`), porque es como lo pide esta API: HttpClient la oculta en
  los logs (`redact`) y nunca registra el texto de las excepciones de requests.
- Además del límite diario hay un límite de ráfaga: "1 request per second" (comprobado el
  20/10/2026: con 3 peticiones seguidas, la 2.ª y la 3.ª recibieron un aviso). Por eso
  esperamos REQUEST_INTERVAL segundos entre símbolos.
- Ojo: cuando algo va mal (límite superado, símbolo inexistente, clave mala) responde 200 con
  un único campo "Information", "Note" o "Error Message" en lugar de datos.
- Condiciones: uso personal y no comercial.

Respuesta (precios como TEXTO; fechas en hora de Nueva York, "US/Eastern"):
    {"Meta Data": {"2. Symbol": "SPY", "3. Last Refreshed": "2026-10-19", ...},
     "Time Series (Daily)": {"2026-10-19": {"1. open": "580.1", ..., "5. volume": "123"}, ...}}
"""

import logging
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path

from marketpulse.common.config import StocksConfig
from marketpulse.common.http import HttpClient, HttpError
from marketpulse.common.storage import DEFAULT_DATA_ROOT, write_bronze
from marketpulse.ingest.errors import (
    MissingApiKeyError,
    PartialIngestError,
    UnexpectedResponseError,
)

logger = logging.getLogger(__name__)

SOURCE = "alphavantage"
QUERY_URL = "https://www.alphavantage.co/query"
API_KEY_ENV = "ALPHAVANTAGE_API_KEY"
SERIES_KEY = "Time Series (Daily)"
# Campos con los que Alpha Vantage avisa de un problema respondiendo 200
NOTICE_KEYS = ("Error Message", "Information", "Note")
# Pausa entre peticiones: el límite es 1/s; dejamos margen por si el reloj o la red varían
REQUEST_INTERVAL = 1.5


def fetch_daily(client: HttpClient, symbol: str, api_key: str) -> dict:
    """Pide la serie diaria (últimos 100 días) de un símbolo."""
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "outputsize": "compact",
        "apikey": api_key,  # se oculta en los logs: ver common/http.py
    }
    data = client.get_json(QUERY_URL, params=params)

    if not isinstance(data, dict):
        raise UnexpectedResponseError(f"Alpha Vantage {symbol}: se esperaba un diccionario")
    for key in NOTICE_KEYS:
        if key in data:
            # Un 200 que en realidad es un error: lo convertimos en excepción con el aviso.
            # Por si el aviso repitiera la clave, la tapamos antes de que llegue a un log.
            notice = str(data[key]).replace(api_key, "***")
            raise UnexpectedResponseError(f"Alpha Vantage {symbol}: {key}: {notice:.200}")
    series = data.get(SERIES_KEY)
    if "Meta Data" not in data or not isinstance(series, dict) or not series:
        raise UnexpectedResponseError(
            f"Alpha Vantage {symbol}: faltan 'Meta Data' o '{SERIES_KEY}': {list(data)}"
        )
    return data


def ingest(
    client: HttpClient,
    stocks: StocksConfig,
    api_key: str | None,
    dt: date | None = None,
    root: Path = DEFAULT_DATA_ROOT,
    sleep: Callable[[float], None] = time.sleep,
) -> list[Path]:
    """Descarga cada símbolo y lo guarda en bronze (un fichero por símbolo).

    Si falla un símbolo se sigue con los demás; al final, si hubo fallos, se lanza
    PartialIngestError para que el programa principal lo sepa (los demás ya están guardados).
    """
    if not api_key:
        # Sin clave no tiene sentido llamar: fallaría cada símbolo y gastaríamos cupo
        raise MissingApiKeyError(f"Alpha Vantage necesita la variable {API_KEY_ENV} (ver .env)")

    paths: list[Path] = []
    failed: dict[str, str] = {}
    for i, asset in enumerate(stocks.assets):
        if i > 0:
            sleep(REQUEST_INTERVAL)  # antes de cada petición salvo la primera
        try:
            data = fetch_daily(client, asset.symbol, api_key)
        except (HttpError, UnexpectedResponseError) as exc:
            logger.error("Alpha Vantage %s falló: %s", asset.symbol, exc)
            failed[asset.symbol] = str(exc)
            continue
        path = write_bronze(SOURCE, data, dt=dt, name=asset.symbol, root=root)
        logger.info(
            "Alpha Vantage %s: %d días guardados en %s", asset.symbol, len(data[SERIES_KEY]), path
        )
        paths.append(path)

    if failed:
        raise PartialIngestError(SOURCE, failed)
    return paths
