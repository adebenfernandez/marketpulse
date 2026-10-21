"""Escritura y lectura de tablas Parquet particionadas por año (layout Hive: year=2026/).

Cada ejecución RECONSTRUYE la tabla entera desde bronze (ver D-015). Para que sea segura:
se escribe en una carpeta temporal y solo al terminar se sustituye la anterior.
"""

import shutil
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PARTITION_COL = "year"


def write_table(df: pd.DataFrame, schema: pa.Schema, table_dir: Path) -> Path:
    """Escribe `df` con el esquema `schema` en `table_dir`, particionado por el año de `date`."""
    # 1) Forzar el esquema: columnas en el orden del contrato y tipos exactos. Si una columna
    #    falta o no se puede convertir (p. ej. texto en `close`), falla AQUÍ, antes de escribir.
    table = pa.Table.from_pandas(df[schema.names], schema=schema, preserve_index=False)

    # 2) Columna de partición: el año del dato (no se guarda dentro del fichero, va en la ruta)
    years = pa.array(pd.to_datetime(df["date"]).dt.year.astype("int32"), type=pa.int32())
    table = table.append_column(PARTITION_COL, years)

    # 3) Escribir en una carpeta temporal hermana; nombres de fichero fijos (part-0.parquet)
    #    para que dos ejecuciones con los mismos datos produzcan exactamente los mismos objetos
    tmp_dir = table_dir.with_name(f".{table_dir.name}.tmp")
    shutil.rmtree(tmp_dir, ignore_errors=True)  # restos de una ejecución interrumpida
    pq.write_to_dataset(
        table,
        root_path=tmp_dir,
        partition_cols=[PARTITION_COL],
        basename_template="part-{i}.parquet",
    )

    # 4) Sustituir la tabla anterior por la nueva. En Windows no se puede renombrar una carpeta
    #    encima de otra que existe, así que: anterior -> .old, nueva -> definitiva, borrar .old
    old_dir = table_dir.with_name(f".{table_dir.name}.old")
    shutil.rmtree(old_dir, ignore_errors=True)
    if table_dir.exists():
        table_dir.rename(old_dir)
    tmp_dir.rename(table_dir)
    shutil.rmtree(old_dir, ignore_errors=True)
    return table_dir


def write_unpartitioned_table(df: pd.DataFrame, schema: pa.Schema, table_dir: Path) -> Path:
    """Como write_table, pero en UN fichero sin particiones (tablas pequeñas: dimensiones)."""
    table = pa.Table.from_pandas(df[schema.names], schema=schema, preserve_index=False)
    table_dir.mkdir(parents=True, exist_ok=True)
    final = table_dir / "part-0.parquet"
    tmp = table_dir / ".part-0.parquet.tmp"  # empieza por punto: s3.py no sube temporales
    pq.write_table(table, tmp)
    tmp.replace(final)  # sustitución atómica, como en la capa bronze
    return table_dir


def read_table(table_dir: Path) -> pd.DataFrame:
    """Lee una tabla particionada (todas sus carpetas year=) como un único DataFrame."""
    return pq.read_table(table_dir).to_pandas()
