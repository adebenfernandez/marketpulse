"""Herramientas del agente: lo ÚNICO que el modelo puede hacer en AWS (D-034).

En el *tool use*, el modelo no ejecuta nada: pide "llama a run_query con esta SQL" y es NUESTRO
código el que decide si lo hace. Por eso aquí están las barreras:
- list_tables y describe_table solo enseñan las tablas de la lista blanca del validador.
- run_query pasa SIEMPRE por validate_sql (guard.py) antes de llegar a Athena, con un LIMIT de
  como máximo MAX_ROWS filas (así el resultado que vuelve al modelo cuesta pocos tokens).
- Los errores se devuelven al modelo como texto (`is_error`), para que pueda corregir su SQL,
  pero nunca con trazas internas ni credenciales.
Cada intento de consulta (bloqueado, fallido o correcto) queda en `self.attempts`, que el bucle
del agente (7.7) vuelca en el registro de auditoría.
"""

import json
import re
from dataclasses import dataclass

from botocore.exceptions import ClientError

from marketpulse.agent.guard import ALLOWED_TABLES, SqlRejectedError, validate_sql
from marketpulse.common.athena import DATABASE, AthenaQueryError, run_query

MAX_ROWS = 100  # filas como máximo por consulta del agente: suficiente para responder, pocos tokens

# Qué es cada tabla, en una línea, para que el modelo elija bien. Las columnas y sus comentarios
# salen de Glue (describe_table); esto añade el "para qué sirve". Un test exige que estén todas.
TABLE_DESCRIPTIONS = {
    "daily_prices": (
        "Tabla gold: un precio por día y activo (formato largo), con clase, moneda, tipo de "
        "precio y fuente. Partición `year`."
    ),
    "dim_asset": (
        "Dimensión de activos (8 filas): nombre, clase (crypto, equity, fx), moneda, tipo de "
        "precio, fuente y días para anualizar (365 cripto, 252 bolsa y divisas)."
    ),
    "dim_date": "Dimensión de fechas desde 2025-01-01 hasta hoy: año, mes, trimestre, día de la "
    "semana, fin de semana.",
    "fact_daily_price": "Hechos del modelo en estrella: (date, asset, price, year). Se cruza con "
    "dim_asset por asset y con dim_date por date.",
    "v_daily_returns": (
        "Rentabilidad diaria de cada activo frente a su sesión ANTERIOR (no el día de calendario "
        "anterior): simple_return, log_return, prev_date, days_since_prev."
    ),
    "v_rolling_volatility_30d": (
        "Volatilidad móvil de 30 sesiones por activo y día, diaria y anualizada (solo filas con "
        "30 observaciones)."
    ),
    "v_correlation_matrix": (
        "Correlación de las rentabilidades de cada pareja de activos en los últimos 90 días, con "
        "fechas alineadas (64 parejas, diagonal 1)."
    ),
    "v_monthly_summary": (
        "Resumen mensual por activo: apertura, cierre, mínimo, máximo, sesiones, rentabilidad del "
        "mes, volatilidad, mejor y peor día, y si el mes está en curso (month_to_date)."
    ),
}

# Definiciones que se envían a la API de Claude (campo `tools`). `strict` obliga a que la entrada
# cumpla el esquema; la descripción es lo que el modelo lee para decidir cuándo usar cada una
TOOL_DEFINITIONS = [
    {
        "name": "list_tables",
        "description": (
            "Lista las tablas y vistas de la base marketpulse que se pueden consultar, con una "
            "línea sobre qué contiene cada una. Úsala primero si no sabes qué tabla usar."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": True,
    },
    {
        "name": "describe_table",
        "description": (
            "Devuelve las columnas (nombre, tipo y comentario) de una tabla o vista de "
            "marketpulse. Úsala antes de escribir SQL sobre una tabla que no has descrito."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "table_name": {"type": "string", "description": "Nombre exacto de la tabla"}
            },
            "required": ["table_name"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "run_query",
        "description": (
            "Ejecuta UNA consulta SELECT de Athena (dialecto Trino) sobre la base marketpulse y "
            f"devuelve como máximo {MAX_ROWS} filas. Solo se admite lectura: cualquier otra cosa "
            "se rechaza y se registra. Si no pones LIMIT, se añade."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"sql": {"type": "string", "description": "Una única sentencia SELECT"}},
            "required": ["sql"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


@dataclass
class QueryAttempt:
    """Un intento de run_query, para el registro de auditoría."""

    sql_proposed: str
    sql_executed: str | None = None
    block_code: str | None = None
    block_reason: str | None = None
    error: str | None = None
    tables: tuple[str, ...] = ()
    bytes_scanned: int = 0
    rows: int = 0


@dataclass(frozen=True)
class ToolResult:
    content: str  # texto (JSON) que vuelve al modelo en el tool_result
    is_error: bool = False


class AgentTools:
    """Ejecuta las herramientas con los clientes de boto3 que se le pasan (o con fakes en tests)."""

    def __init__(self, glue_client, athena_client):
        self.glue = glue_client
        self.athena = athena_client
        self.attempts: list[QueryAttempt] = []
        self._columns_cache: dict[str, dict] = {}  # el esquema no cambia durante una pregunta

    def execute(self, name: str, tool_input: dict) -> ToolResult:
        """Punto de entrada único: el bucle del agente solo llama aquí."""
        if name == "list_tables":
            return self.list_tables()
        if name == "describe_table":
            return self.describe_table(str(tool_input.get("table_name", "")))
        if name == "run_query":
            return self.run_query(str(tool_input.get("sql", "")))
        return _error(f"Herramienta desconocida: {name}")

    def list_tables(self) -> ToolResult:
        tables = [
            {"name": name, "description": TABLE_DESCRIPTIONS[name]}
            for name in sorted(ALLOWED_TABLES)
        ]
        return _ok({"database": DATABASE, "tables": tables})

    def describe_table(self, table_name: str) -> ToolResult:
        name = table_name.strip().lower()
        if name not in ALLOWED_TABLES:  # ni siquiera se pregunta a Glue por otras tablas
            return _error(f"La tabla {table_name!r} no existe o no se puede consultar")
        if name not in self._columns_cache:
            table = self.glue.get_table(DatabaseName=DATABASE, Name=name)["Table"]
            storage = table.get("StorageDescriptor", {})
            columns = [_column(c) for c in storage.get("Columns", [])]
            partitions = [_column(c) for c in table.get("PartitionKeys", [])]
            self._columns_cache[name] = {
                "name": name,
                "kind": "view" if table.get("TableType") == "VIRTUAL_VIEW" else "table",
                "description": TABLE_DESCRIPTIONS[name],
                "columns": columns + partitions,
                "partition_columns": [p["name"] for p in partitions],
            }
        return _ok(self._columns_cache[name])

    def run_query(self, sql: str) -> ToolResult:
        attempt = QueryAttempt(sql_proposed=sql)
        self.attempts.append(attempt)
        try:
            validated = validate_sql(sql, max_limit=MAX_ROWS)
        except SqlRejectedError as e:
            attempt.block_code, attempt.block_reason = e.code, e.reason
            return _error(f"Consulta rechazada por seguridad ({e.code}): {e.reason}")

        attempt.sql_executed = validated.sql
        attempt.tables = validated.tables
        try:
            result = run_query(self.athena, validated.sql)
        except (AthenaQueryError, ClientError) as e:
            # AthenaQueryError: la consulta empezó y terminó en FAILED. ClientError: Athena la
            # rechazó al lanzarla (p. ej. InvalidRequestException por un error de sintaxis, como
            # unas comillas tipográficas “date” en la evaluación del paso 7.8). En los dos casos,
            # el modelo recibe el error y puede corregir la SQL
            attempt.error = str(e)  # completo en el registro local
            # Al modelo (y de ahí al usuario) sin números de cuenta: los mensajes de Athena
            # incluyen ARN como arn:aws:sts::123456789012:assumed-role/...
            return _error(f"Athena no pudo ejecutar la consulta: {_hide_account(str(e))}")

        attempt.bytes_scanned = result.bytes_scanned
        attempt.rows = len(result.rows)
        return _ok(
            {
                "sql_executed": validated.sql,
                "columns": result.columns,
                "rows": result.rows,
                "row_count": len(result.rows),
                "limit": validated.limit,
                "bytes_scanned": result.bytes_scanned,
            }
        )


def _hide_account(text: str) -> str:
    return re.sub(r"\b\d{12}\b", "<cuenta>", text)


def _column(c: dict) -> dict:
    return {"name": c["Name"], "type": c["Type"], "comment": c.get("Comment", "")}


def _ok(data: dict) -> ToolResult:
    return ToolResult(json.dumps(data, ensure_ascii=False))


def _error(message: str) -> ToolResult:
    return ToolResult(json.dumps({"error": message}, ensure_ascii=False), is_error=True)
