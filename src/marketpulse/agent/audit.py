"""Registro de auditoría del agente: una línea JSON por pregunta (D-031).

Es la cuarta capa de la defensa en profundidad: no impide nada, pero deja constancia de TODO
lo que se ha preguntado y de qué pasó (respondida, bloqueada por el validador, rechazada por el
modelo o error), con la SQL, los bytes escaneados y el coste en tokens. Sirve para:
- demostrar que un ataque se bloqueó (criterio 2 de la Fase 7),
- investigar después qué pidió alguien y qué SQL se ejecutó,
- sumar el gasto de la API de Claude.

Formato JSON Lines (un objeto JSON por línea): se puede añadir sin reescribir el fichero, y
`json.dumps` escapa los saltos de línea, así que una pregunta con "\\n{...}" no puede fabricar
una línea falsa en el registro (inyección en logs).

Destinos: el fichero `logs/agent_audit.jsonl` (o el de MARKETPULSE_AUDIT_LOG), ignorado por Git,
y el logger `marketpulse.agent.audit` (en Docker sale por la salida estándar). Nunca se registra
ninguna clave: el registro solo recibe lo que se le pasa en AuditRecord.
"""

import json
import logging
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger("marketpulse.agent.audit")

OUTCOMES = ("respondida", "bloqueada", "rechazada", "error")
MAX_TEXT_CHARS = 4_000  # una pregunta o una SQL más larga se recorta en el registro
DEFAULT_PATH = Path("logs") / "agent_audit.jsonl"


def _now_utc() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


@dataclass
class AuditRecord:
    question: str
    outcome: str  # uno de OUTCOMES
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: str = field(default_factory=_now_utc)
    sql_proposed: str | None = None  # la SQL que escribió el modelo
    sql_executed: str | None = None  # la SQL validada que llegó a Athena (con LIMIT)
    block_code: str | None = None  # código de SqlRejectedError, si se bloqueó
    block_reason: str | None = None
    tables: list[str] = field(default_factory=list)
    bytes_scanned: int | None = None
    usage: dict | None = None  # TokenUsage.as_dict()
    elapsed_ms: int | None = None
    detail: str | None = None  # tipo de error o motivo del rechazo del modelo (corto)
    queries: list[dict] = field(default_factory=list)  # todos los intentos de run_query (7.7)


def _clip(value):
    if isinstance(value, str) and len(value) > MAX_TEXT_CHARS:
        return value[:MAX_TEXT_CHARS] + f"…[+{len(value) - MAX_TEXT_CHARS} caracteres]"
    return value


class AuditLog:
    """Escribe AuditRecord en un fichero JSONL y en el logger. Seguro con varios hilos."""

    def __init__(self, path: Path | None):
        self.path = path  # None = solo el logger (p. ej., en algunos tests)
        self._lock = threading.Lock()  # FastAPI atiende peticiones en varios hilos a la vez

    def write(self, record: AuditRecord) -> str:
        """Devuelve la línea escrita. Si no se puede escribir, el error sube: no se calla."""
        if record.outcome not in OUTCOMES:
            raise ValueError(f"outcome desconocido: {record.outcome!r}")
        data = {key: _clip(value) for key, value in asdict(record).items()}
        line = json.dumps(data, ensure_ascii=False, sort_keys=True)

        if self.path is not None:
            with self._lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")

        # Lo bloqueado y lo rechazado es lo que hay que mirar: WARNING para que destaque
        level = {"respondida": logging.INFO, "error": logging.ERROR}.get(
            record.outcome, logging.WARNING
        )
        logger.log(level, "auditoria %s", line)
        return line


def default_audit_log() -> AuditLog:
    """El registro por defecto: MARKETPULSE_AUDIT_LOG si está definida, si no logs/."""
    return AuditLog(Path(os.environ.get("MARKETPULSE_AUDIT_LOG", DEFAULT_PATH)))
