"""Lectura de la capa bronze (local): recorre las particiones source=/dt= y devuelve cada JSON."""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from marketpulse.common.storage import DEFAULT_DATA_ROOT


@dataclass(frozen=True)
class BronzeFile:
    source: str
    ingest_date: date  # el dt= de la carpeta: CUÁNDO se descargó (no a qué día se refiere)
    name: str  # nombre del fichero sin .json (frankfurter, SPY...)
    payload: dict | list  # el JSON tal cual lo devolvió la API


def iter_bronze(source: str, root: Path = DEFAULT_DATA_ROOT) -> Iterator[BronzeFile]:
    """Devuelve los ficheros bronze de una fuente, del día más antiguo al más reciente."""
    source_dir = root / "bronze" / f"source={source}"
    # sorted(): el orden importa para deduplicar (el último gana). "dt=2026-10-20" se ordena bien
    # como texto porque la fecha está en formato AAAA-MM-DD.
    for partition in sorted(source_dir.glob("dt=*")):
        ingest_date = date.fromisoformat(partition.name.removeprefix("dt="))
        for path in sorted(partition.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            yield BronzeFile(source, ingest_date, path.stem, payload)
