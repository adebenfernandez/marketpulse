"""Handler de la Lambda de ingesta: descarga las tres fuentes y sube bronze a S3.

Lambda llama a `handler(event, context)` (configurado en Terraform como
"marketpulse.ingest.handler.handler"). Pasos:
  1. Leer las claves de API de SSM Parameter Store (en Lambda no hay .env).
  2. Ejecutar la misma ingesta que en local (run_all) en una carpeta temporal de /tmp.
  3. Subir a S3 lo descargado, aunque alguna fuente haya fallado (no perder lo que sí llegó).
  4. Si alguna fuente falló, LANZAR JobFailedError: Lambda lo cuenta como error (alarma, reintento).
"""

import logging
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path

from marketpulse.common.config import DEFAULT_WATCHLIST_PATH, load_watchlist
from marketpulse.common.http import HttpClient
from marketpulse.common.lambda_runtime import JobFailedError, configure_logging, require_env
from marketpulse.common.s3 import BUCKET_ENV, upload_layers
from marketpulse.common.ssm import get_parameters
from marketpulse.ingest import alphavantage, coingecko
from marketpulse.ingest.run import run_all

logger = logging.getLogger(__name__)

# Clave que espera run_all -> variable de entorno de la Lambda con el NOMBRE del parámetro de SSM.
# Terraform rellena esas variables con el nombre (no secreto); el valor solo lo tiene SSM.
SECRET_PARAMS = {
    coingecko.API_KEY_ENV: "COINGECKO_API_KEY_PARAM",
    alphavantage.API_KEY_ENV: "ALPHAVANTAGE_API_KEY_PARAM",
}


def run_ingest_job(s3_client, ssm_client, env: Mapping[str, str], http, root: Path) -> dict:
    """La lógica del handler, con los clientes INYECTADOS para poder probarla sin AWS."""
    bucket = require_env(env, BUCKET_ENV)
    param_names = {key: require_env(env, var) for key, var in SECRET_PARAMS.items()}
    secrets = get_parameters(ssm_client, param_names)

    # Las claves se mezclan con el entorno SOLO en este diccionario: no se escriben en os.environ
    # (no se heredarían a otros procesos ni se quedarían en la memoria del entorno de ejecución)
    job_env = {**env, **secrets}
    watchlist = load_watchlist(env.get("MARKETPULSE_WATCHLIST", DEFAULT_WATCHLIST_PATH))

    results = run_all(watchlist, http, job_env, root=root)
    upload = upload_layers(s3_client, bucket, root=root, layers=("bronze",))

    failed = {name: error for name, error in results.items() if error is not None}
    summary = {"sources_ok": sorted(set(results) - set(failed)), "failed": failed, **upload}
    logger.info("Resumen: %s", summary)
    if failed:
        raise JobFailedError(f"Ingesta: fallaron {len(failed)} fuente(s): {sorted(failed)}")
    return summary


def handler(event, context):
    """Punto de entrada de Lambda. `event` (lo que manda EventBridge) no se usa."""
    import boto3  # aquí y no arriba: los tests importan este módulo sin necesitar boto3

    configure_logging(os.environ)
    # /tmp es el único disco escribible en Lambda (512 MB gratis). TemporaryDirectory crea una
    # carpeta nueva en cada ejecución y la borra al terminar: si el entorno se reutiliza
    # ("arranque en caliente"), no quedan ficheros de la ejecución anterior
    with tempfile.TemporaryDirectory(prefix="marketpulse-") as tmp:
        return run_ingest_job(
            s3_client=boto3.client("s3"),
            ssm_client=boto3.client("ssm"),
            env=os.environ,
            http=HttpClient(),
            root=Path(tmp),
        )
