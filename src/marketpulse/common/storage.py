"""Escritura de la capa bronze en local: respuesta original de la API, particionada e idempotente.

Estructura (estilo Hive, la que entenderá Athena en la Fase 4):
    data/bronze/source=<fuente>/dt=<AAAA-MM-DD>/<nombre>.json

En la Fase 2 el destino pasará a ser S3, pero la estructura de rutas será la misma.
"""

import json
import os
import re
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path

DEFAULT_DATA_ROOT = Path("data")

# Solo letras, números, guion y guion bajo. Impide nombres como "../../Windows" (path traversal)
_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


def utc_today() -> date:
    """La fecha de hoy en UTC. Igual en el portátil (hora de España) que en Lambda (UTC)."""
    return datetime.now(UTC).date()


def _check_name(value: str, what: str) -> None:
    if not _SAFE_NAME.fullmatch(value):
        raise ValueError(f"{what} no válido: {value!r} (solo letras, números, '-' y '_')")


def bronze_path(
    source: str, dt: date, name: str | None = None, root: Path = DEFAULT_DATA_ROOT
) -> Path:
    """Ruta del fichero bronze. Depende SOLO de fuente, fecha y nombre: eso la hace idempotente."""
    name = name or source
    _check_name(source, "Nombre de fuente")
    _check_name(name, "Nombre de fichero")
    return root / "bronze" / f"source={source}" / f"dt={dt.isoformat()}" / f"{name}.json"


def write_bronze(
    source: str,
    payload: dict | list,
    dt: date | None = None,
    name: str | None = None,
    root: Path = DEFAULT_DATA_ROOT,
) -> Path:
    """Guarda `payload` (la respuesta JSON de la API, sin modificar) y devuelve la ruta escrita.

    Si el fichero ya existe (segunda ejecución del mismo día), se SOBRESCRIBE: nunca se duplica.
    """
    path = bronze_path(source, dt or utc_today(), name, root)
    path.parent.mkdir(parents=True, exist_ok=True)  # crea las carpetas de la partición si faltan

    # Pasamos a texto ANTES de tocar el disco: si el payload no es serializable, no se escribe nada
    text = json.dumps(payload, ensure_ascii=False, indent=2)

    # Escritura atómica: 1) fichero temporal en la MISMA carpeta  2) renombrar encima del final.
    # os.replace es atómico: quien lea verá el fichero viejo completo o el nuevo completo, nunca
    # uno a medias. Tiene que ser la misma carpeta (mismo disco) para que el renombrado sea atómico.
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.stem}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        # Si algo falla (disco lleno, Ctrl+C...), borramos el temporal y dejamos el fichero anterior
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return path
