"""Handler de la Lambda de transformación: bronze (S3) -> silver y gold (S3), con calidad.

Lambda llama a `handler(event, context)` ("marketpulse.transform.handler.handler"). Pasos:
  1. Descargar TODO bronze de S3 a una carpeta temporal de /tmp.
  2. Ejecutar la misma transformación que en local (run_transform): construir, comprobar calidad
     y escribir silver y gold solo si no hay errores.
  3. Si la calidad falla, LANZAR JobFailedError y no subir nada: en S3 se queda la última versión
     buena de silver y gold.
  4. Si todo va bien, subir silver y gold (solo los ficheros que han cambiado).
"""

import logging
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path

from marketpulse.common.config import DEFAULT_WATCHLIST_PATH, load_watchlist
from marketpulse.common.lambda_runtime import JobFailedError, configure_logging, require_env
from marketpulse.common.s3 import BUCKET_ENV, download_layer, upload_layers
from marketpulse.transform.run import run_transform

logger = logging.getLogger(__name__)


def log_versions() -> None:
    """Deja en el log las versiones reales de pandas y pyarrow (las de la capa de AWS)."""
    import pandas
    import pyarrow

    logger.info("Versiones: pandas %s, pyarrow %s", pandas.__version__, pyarrow.__version__)


def run_transform_job(s3_client, env: Mapping[str, str], root: Path) -> dict:
    """La lógica del handler, con el cliente de S3 INYECTADO para poder probarla sin AWS."""
    bucket = require_env(env, BUCKET_ENV)
    watchlist = load_watchlist(env.get("MARKETPULSE_WATCHLIST", DEFAULT_WATCHLIST_PATH))

    downloaded = download_layer(s3_client, bucket, "bronze", root)
    if downloaded == 0:
        raise JobFailedError(f"No hay nada en s3://{bucket}/bronze/: ¿ha fallado la ingesta?")

    if not run_transform(watchlist, root=root):
        raise JobFailedError("Transformación: la calidad de datos ha fallado (ver el log)")

    upload = upload_layers(s3_client, bucket, root=root, layers=("silver", "gold"))
    summary = {"bronze_downloaded": downloaded, **upload}
    logger.info("Resumen: %s", summary)
    return summary


def handler(event, context):
    """Punto de entrada de Lambda. `event` (lo que manda EventBridge) no se usa."""
    import boto3

    configure_logging(os.environ)
    log_versions()
    with tempfile.TemporaryDirectory(prefix="marketpulse-") as tmp:
        return run_transform_job(s3_client=boto3.client("s3"), env=os.environ, root=Path(tmp))
