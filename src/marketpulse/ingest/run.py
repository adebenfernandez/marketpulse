"""Orquestador de la ingesta: ejecuta las tres fuentes, resume el resultado y da código de salida.

Se usa desde `python -m marketpulse.ingest` (ver __main__.py) y, en la Fase 3, desde el
handler de Lambda, que llamará a run_all() directamente.
"""

import logging
import os
from collections.abc import Callable, Mapping
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from marketpulse.common.config import DEFAULT_WATCHLIST_PATH, Watchlist, load_watchlist
from marketpulse.common.http import HttpClient
from marketpulse.common.storage import DEFAULT_DATA_ROOT, utc_today
from marketpulse.ingest import alphavantage, coingecko, frankfurter

logger = logging.getLogger(__name__)

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def get_secret(env: Mapping[str, str], name: str) -> str | None:
    """Lee una clave del entorno. Vacía o solo espacios cuenta como "no hay clave" (None)."""
    value = (env.get(name) or "").strip()  # .strip() quita espacios y saltos de línea sobrantes
    return value or None


def run_all(
    watchlist: Watchlist,
    client: HttpClient,
    env: Mapping[str, str],
    dt: date | None = None,
    root: Path = DEFAULT_DATA_ROOT,
) -> dict[str, str | None]:
    """Ejecuta cada fuente aunque otra falle. Devuelve {fuente: None si fue bien, o el error}."""
    dt = dt or utc_today()  # una sola fecha para todas las fuentes, aunque pase la medianoche

    # Cada fuente es una función sin argumentos: así el bucle de abajo las trata a todas igual
    sources: dict[str, Callable[[], object]] = {
        frankfurter.SOURCE: lambda: frankfurter.ingest(client, watchlist.fx, dt=dt, root=root),
        coingecko.SOURCE: lambda: coingecko.ingest(
            client, watchlist.crypto, get_secret(env, coingecko.API_KEY_ENV), dt=dt, root=root
        ),
        alphavantage.SOURCE: lambda: alphavantage.ingest(
            client, watchlist.stocks, get_secret(env, alphavantage.API_KEY_ENV), dt=dt, root=root
        ),
    }

    results: dict[str, str | None] = {}
    for name, ingest_source in sources.items():
        try:
            ingest_source()
            results[name] = None
        except Exception as exc:
            # Aquí SÍ atrapamos cualquier error: es la última línea de defensa, y un fallo en
            # una fuente no debe impedir que se descarguen las demás. logger.exception añade la
            # traza completa para poder depurarlo (nuestros errores no llevan claves dentro).
            logger.exception("Fuente %s falló", name)
            results[name] = f"{type(exc).__name__}: {exc}"
    return results


def main(env: Mapping[str, str] | None = None) -> int:
    """Punto de entrada. Devuelve el código de salida: 0 = todo bien, 1 = alguna fuente falló."""
    # Lee .env (si existe) y lo añade a las variables de entorno, sin pisar las ya definidas.
    # En Lambda no habrá .env: las variables vendrán de su configuración y de SSM.
    load_dotenv()
    env = os.environ if env is None else env
    logging.basicConfig(level=env.get("LOG_LEVEL", "INFO").upper(), format=LOG_FORMAT)

    watchlist = load_watchlist(env.get("MARKETPULSE_WATCHLIST", DEFAULT_WATCHLIST_PATH))
    results = run_all(watchlist, HttpClient(), env)

    ok = [name for name, error in results.items() if error is None]
    failed = {name: error for name, error in results.items() if error is not None}
    logger.info("Resumen: %d/%d fuentes correctas %s", len(ok), len(results), ok)
    for name, error in failed.items():
        logger.error("Resumen: %s FALLÓ -> %s", name, error)
    return 1 if failed else 0
