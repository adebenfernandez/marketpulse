"""Ejecutar SQL en Athena desde Python y ver cuántos bytes ha leído cada consulta.

Athena es asíncrono: start_query_execution devuelve un id al momento, la consulta se ejecuta en
segundo plano y hay que preguntar su estado hasta que termine. Este módulo esconde ese ciclo.
Lo usan el despliegue de las vistas (paso 4.5) y, más adelante, el agente text-to-SQL (Fase 7).

Uso desde la terminal (con AWS_PROFILE=marketpulse):
    python -m marketpulse.common.athena "SELECT asset_class, count(*) FROM daily_prices GROUP BY 1"
    python -m marketpulse.common.athena --file sql/consulta.sql
    python -m marketpulse.common.athena --deploy-views sql/views   (lo lanza Terraform, paso 4.5)
"""

import argparse
import logging
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("marketpulse.common.athena")

WORKGROUP = "marketpulse"  # el workgroup del paso 4.3 (límite de 100 MB, resultados con 7 días)
DATABASE = "marketpulse"  # la base de datos de Glue del paso 4.4
FINAL_STATES = {"SUCCEEDED", "FAILED", "CANCELLED"}


class AthenaQueryError(RuntimeError):
    """La consulta terminó en FAILED o CANCELLED (p. ej. por superar el límite de bytes)."""


@dataclass(frozen=True)
class QueryResult:
    query_id: str
    columns: list[str]
    rows: list[list[str | None]]  # Athena devuelve todos los valores como texto
    bytes_scanned: int  # lo que se cobra: 5 USD por TB
    elapsed_ms: int


def run_query(
    client,
    sql: str,
    workgroup: str = WORKGROUP,
    database: str = DATABASE,
    timeout_s: float = 120,
    poll_s: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
) -> QueryResult:
    """Lanza `sql`, espera a que termine y devuelve las filas y los bytes leídos."""
    query_id = client.start_query_execution(
        QueryString=sql,
        WorkGroup=workgroup,  # la ubicación de resultados y el límite los pone el workgroup
        QueryExecutionContext={"Database": database},  # para no escribir marketpulse.tabla
    )["QueryExecutionId"]

    waited = 0.0
    while True:
        execution = client.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]
        state = execution["Status"]["State"]
        if state in FINAL_STATES:
            break
        if waited >= timeout_s:
            client.stop_query_execution(QueryExecutionId=query_id)
            raise AthenaQueryError(f"Consulta {query_id} sin terminar tras {timeout_s} s")
        sleep(poll_s)
        waited += poll_s

    stats = execution.get("Statistics", {})
    if state != "SUCCEEDED":
        reason = execution["Status"].get("StateChangeReason", "sin motivo")
        raise AthenaQueryError(f"Consulta {query_id} {state}: {reason}")

    columns, rows = [], []
    paginator = client.get_paginator("get_query_results")  # más de 1.000 filas = varias páginas
    for page in paginator.paginate(QueryExecutionId=query_id):
        result_set = page["ResultSet"]
        if not columns:
            columns = [c["Name"] for c in result_set["ResultSetMetadata"]["ColumnInfo"]]
        rows += [[d.get("VarCharValue") for d in r["Data"]] for r in result_set["Rows"]]
    # En un SELECT, la primera fila que devuelve Athena son los nombres de las columnas
    if execution.get("StatementType") == "DML" and rows and rows[0] == columns:
        rows = rows[1:]

    return QueryResult(
        query_id=query_id,
        columns=columns,
        rows=rows,
        bytes_scanned=stats.get("DataScannedInBytes", 0),
        elapsed_ms=stats.get("TotalExecutionTimeInMillis", 0),
    )


def sql_from_file(path: Path) -> str:
    """Lee un .sql: quita los comentarios de cabecera (líneas "--" del principio) y el ";" final.

    La API de Athena acepta UNA sentencia sin ";" final. Los comentarios de dentro de la
    sentencia se conservan (quedan guardados en la definición de la vista).
    """
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    while lines and (not lines[0].strip() or lines[0].lstrip().startswith("--")):
        lines.pop(0)
    return "\n".join(lines).strip().rstrip(";").strip()


def deploy_views(client, directory: Path, **kwargs) -> list[str]:
    """Ejecuta cada .sql de `directory` en orden alfabético (01_..., 02_...).

    El orden importa: una vista puede usar otra (v_daily_returns usa fact_daily_price), así que
    las de base llevan un número menor. Cada fichero hace CREATE OR REPLACE VIEW: repetirlo es
    seguro (idempotente).
    """
    deployed = []
    for path in sorted(directory.glob("*.sql")):
        run_query(client, sql_from_file(path), **kwargs)
        logger.info("Vista desplegada: %s", path.name)
        deployed.append(path.name)
    if not deployed:
        raise AthenaQueryError(f"No hay ficheros .sql en {directory}")
    return deployed


def format_table(result: QueryResult, max_rows: int = 50) -> str:
    """Tabla de texto con columnas alineadas, para leerla en la terminal."""
    shown = [[v if v is not None else "NULL" for v in r] for r in result.rows[:max_rows]]
    widths = [max(len(c), *(len(r[i]) for r in shown)) for i, c in enumerate(result.columns)]
    lines = [" | ".join(c.ljust(w) for c, w in zip(result.columns, widths, strict=True))]
    lines.append("-+-".join("-" * w for w in widths))
    lines += [" | ".join(v.ljust(w) for v, w in zip(r, widths, strict=True)) for r in shown]
    if len(result.rows) > max_rows:
        lines.append(f"... ({len(result.rows) - max_rows} filas más)")
    return "\n".join(lines)


def main() -> int:
    import boto3

    parser = argparse.ArgumentParser(prog="python -m marketpulse.common.athena")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("sql", nargs="?", help="consulta SQL entre comillas")
    group.add_argument("--file", type=Path, help="fichero .sql con UNA consulta")
    group.add_argument("--deploy-views", type=Path, help="carpeta con las vistas (sql/views)")
    args = parser.parse_args()

    logging.basicConfig(level="INFO", format="%(levelname)s %(name)s: %(message)s")
    client = boto3.client("athena", region_name=os.environ.get("AWS_REGION", "eu-north-1"))
    try:
        if args.deploy_views:
            deploy_views(client, args.deploy_views)
            return 0
        result = run_query(client, sql_from_file(args.file) if args.file else args.sql)
    except AthenaQueryError as exc:
        print(f"ERROR: {exc}")
        return 1
    if result.columns:
        print(format_table(result))
    print(
        f"\n{len(result.rows)} filas | {result.bytes_scanned:,} bytes escaneados | "
        f"{result.elapsed_ms} ms | id {result.query_id}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
