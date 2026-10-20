"""Orquestador de la transformación: bronze -> silver -> gold, con comprobaciones de calidad.

Se ejecuta con `python -m marketpulse.transform`. Orden (fail fast):
  1. Construir silver y gold EN MEMORIA.
  2. Comprobar la calidad de las dos capas.
  3. Solo si no hay ningún ERROR, escribirlas. Si lo hay, no se toca nada en disco: silver y gold
     se quedan como estaban (la última versión buena) y el proceso termina con código 1.
A diferencia de la ingesta, aquí no se sigue adelante si algo falla: gold depende de silver.
"""

import logging
import os
from datetime import date
from pathlib import Path

from marketpulse.common.config import DEFAULT_WATCHLIST_PATH, Watchlist, load_watchlist
from marketpulse.common.storage import DEFAULT_DATA_ROOT, utc_today
from marketpulse.ingest.run import LOG_FORMAT
from marketpulse.quality.rules import check_gold, check_silver, has_errors, log_report
from marketpulse.transform.gold import daily_prices_from, write_gold
from marketpulse.transform.silver import build_silver_frames, write_silver

logger = logging.getLogger(__name__)


def run_transform(
    watchlist: Watchlist, root: Path = DEFAULT_DATA_ROOT, today: date | None = None
) -> bool:
    """Construye, comprueba y, si todo va bien, escribe silver y gold. True = se ha publicado."""
    silver = build_silver_frames(watchlist, root)
    gold = daily_prices_from(silver, watchlist)

    results = check_silver(silver) + check_gold(gold, watchlist, today or utc_today())
    log_report(results)
    if has_errors(results):
        logger.error("Calidad: hay errores. NO se escribe silver ni gold (se conserva lo anterior)")
        return False

    written = write_silver(silver, root) | write_gold(gold, root)
    logger.info("Publicado: %s", sorted(written))
    return True


def main() -> int:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper(), format=LOG_FORMAT)
    watchlist = load_watchlist(os.environ.get("MARKETPULSE_WATCHLIST", DEFAULT_WATCHLIST_PATH))
    return 0 if run_transform(watchlist) else 1
