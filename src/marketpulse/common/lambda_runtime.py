"""Piezas comunes a los handlers de Lambda (ingesta y transformación)."""

import logging
from collections.abc import Mapping

from marketpulse.ingest.run import LOG_FORMAT


class JobFailedError(RuntimeError):
    """El trabajo terminó mal. Se LANZA (no se devuelve) para que Lambda lo cuente como error.

    Si el handler devolviera {"status": "error"}, para Lambda sería una ejecución correcta: no
    subiría la métrica Errors, no saltaría la alarma y no se reintentaría. Lanzar la excepción
    es la forma de decirle a Lambda "esto ha fallado".
    """


def configure_logging(env: Mapping[str, str]) -> None:
    """Nivel de log desde LOG_LEVEL (INFO por defecto).

    En Lambda el registrador raíz ya trae un manejador que envía cada línea a CloudWatch Logs
    (con la hora y el id de la petición), así que solo cambiamos el nivel. Fuera de Lambda (tests,
    local) no hay manejador y añadimos uno con el mismo formato que la ingesta local.
    """
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(format=LOG_FORMAT)
    root.setLevel(env.get("LOG_LEVEL", "INFO").upper())


def require_env(env: Mapping[str, str], name: str) -> str:
    """Variable de entorno obligatoria (la pone Terraform en la configuración de la Lambda)."""
    value = (env.get(name) or "").strip()
    if not value:
        raise JobFailedError(f"Falta la variable de entorno {name}")
    return value
