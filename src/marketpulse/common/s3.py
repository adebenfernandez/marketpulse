"""Subida del data lake local (data/) al bucket de S3, con las mismas rutas.

    data/bronze/source=frankfurter/dt=2026-10-20/frankfurter.json
      -> s3://<bucket>/bronze/source=frankfurter/dt=2026-10-20/frankfurter.json

Reglas:
- Solo SUBE, nunca borra nada en S3. Los nombres de fichero son fijos (`part-0.parquet`, la fecha
  en bronze), así que volver a subir SOBRESCRIBE el mismo objeto: no se duplica nada.
- Solo sube lo que ha CAMBIADO: compara la huella MD5 del fichero local con la etiqueta (ETag)
  que S3 guarda de cada objeto. Ahorra peticiones PUT y hace visible la idempotencia.

Se ejecuta con `python -m marketpulse.common.s3` (necesita MARKETPULSE_BUCKET en el entorno).
"""

import hashlib
import logging
import os
import sys
from pathlib import Path

from marketpulse.common.storage import DEFAULT_DATA_ROOT

# Nombre fijo: con `python -m`, __name__ vale "__main__" y el log no diría de qué módulo viene
logger = logging.getLogger("marketpulse.common.s3")

LAYERS = ("bronze", "silver", "gold")
BUCKET_ENV = "MARKETPULSE_BUCKET"
CONTENT_TYPES = {".json": "application/json", ".parquet": "application/vnd.apache.parquet"}


def s3_key(path: Path, root: Path) -> str:
    """Clave S3 de un fichero local. En Windows la ruta usa '\\', pero en S3 el separador es '/'."""
    return path.relative_to(root).as_posix()


def md5_hex(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def local_files(root: Path, layer: str) -> list[Path]:
    """Ficheros de una capa, sin los temporales (.tmp, .old: empiezan por punto)."""
    base = root / layer
    if not base.exists():
        return []
    return sorted(
        p
        for p in base.rglob("*")
        if p.is_file() and not any(part.startswith(".") for part in p.relative_to(root).parts)
    )


def remote_etags(client, bucket: str, prefix: str) -> dict[str, str]:
    """{clave: ETag} de los objetos que ya hay en S3 bajo `prefix`.

    list_objects_v2 devuelve como mucho 1.000 objetos por respuesta: el paginador pide las
    páginas siguientes por nosotros.
    """
    etags = {}
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            etags[obj["Key"]] = obj["ETag"].strip('"')  # S3 devuelve el ETag entre comillas
    return etags


def upload_layers(
    client, bucket: str, root: Path = DEFAULT_DATA_ROOT, layers=LAYERS
) -> dict[str, int]:
    """Sube las capas a S3. Devuelve {"uploaded": n, "unchanged": m}."""
    uploaded = unchanged = 0
    for layer in layers:
        existing = remote_etags(client, bucket, f"{layer}/")
        for path in local_files(root, layer):
            key = s3_key(path, root)
            digest = md5_hex(path)
            # Con put_object (una sola petición, sin subida multiparte) y cifrado SSE-S3, el ETag
            # de S3 es exactamente el MD5 del contenido: si coinciden, el objeto ya está al día
            if existing.get(key) == digest:
                unchanged += 1
                continue
            client.put_object(
                Bucket=bucket,
                Key=key,
                Body=path.read_bytes(),
                ContentType=CONTENT_TYPES.get(path.suffix, "application/octet-stream"),
            )
            logger.info("Subido s3://%s/%s (%d bytes)", bucket, key, path.stat().st_size)
            uploaded += 1
    logger.info("S3: %d subidos, %d sin cambios", uploaded, unchanged)
    return {"uploaded": uploaded, "unchanged": unchanged}


def download_layer(client, bucket: str, layer: str, root: Path) -> int:
    """Descarga una capa entera de S3 a `root`, con las mismas rutas. Devuelve cuántos objetos.

    Lo usa la Lambda de transformación: necesita TODO bronze en su disco temporal (/tmp) para
    reconstruir silver y gold, igual que hace el código en local con la carpeta data/.
    """
    root = root.resolve()
    count = 0
    for key in sorted(remote_etags(client, bucket, f"{layer}/")):
        path = (root / key).resolve()
        # Defensa contra path traversal: una clave como "bronze/../../etc/x" no puede escribir
        # fuera de `root`. En nuestro bucket no debería existir, pero no cuesta nada comprobarlo
        if not path.is_relative_to(root):
            raise ValueError(f"Clave de S3 fuera de la carpeta de destino: {key!r}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(client.get_object(Bucket=bucket, Key=key)["Body"].read())
        count += 1
    logger.info("S3: %d objetos descargados de s3://%s/%s/", count, bucket, layer)
    return count


def main() -> int:
    import boto3  # aquí y no arriba: los tests no necesitan cargar boto3 ni tener credenciales
    from dotenv import load_dotenv

    from marketpulse.ingest.run import LOG_FORMAT

    load_dotenv()
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper(), format=LOG_FORMAT)
    bucket = os.environ.get(BUCKET_ENV, "").strip()
    if not bucket:
        logger.error("Falta la variable %s (nombre del bucket, ver .env.example)", BUCKET_ENV)
        return 1
    # boto3 busca las credenciales como la AWS CLI: AWS_PROFILE=marketpulse en local
    client = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "eu-north-1"))
    upload_layers(client, bucket)
    return 0


if __name__ == "__main__":
    sys.exit(main())
