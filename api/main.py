"""API HTTP del agente text-to-SQL (paso 7.9, D-037).

    GET  /health  → {"status": "ok"}  (no llama a AWS ni a Claude: para saber si el servicio vive)
    POST /ask     → {"question": "..."} → respuesta, SQL usada, explicación, tokens y coste

Se ejecuta en Docker (api/Dockerfile) con uvicorn. Las credenciales llegan por variables de
entorno: ANTHROPIC_API_KEY y las credenciales TEMPORALES del rol marketpulse-agent (1 h), que
pone scripts/run_agent_docker.ps1. Fuera de Docker, MARKETPULSE_ASSUME_ROLE=1 hace que la API se
ponga ella misma el rol a partir de la sesión de `aws login`.

Toda la lógica está en marketpulse.agent; aquí solo se traduce HTTP ⇄ Agent.ask.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from marketpulse.agent.runtime import MissingApiKeyError, aws_session, build_agent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("marketpulse.api")

MAX_QUESTION_CHARS = 1_000  # una pregunta normal ocupa una línea; más es abuso o un ataque


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=MAX_QUESTION_CHARS)


class Usage(BaseModel):
    model: str
    calls: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_usd: float


class AskResponse(BaseModel):
    request_id: str
    outcome: str  # respondida · bloqueada · rechazada · error
    answer: str
    sql: str
    explanation: str
    bytes_scanned: int
    elapsed_ms: int
    usage: Usage


def create_agent():
    """Se monta UNA vez al arrancar. Si falta la clave, la API arranca igual y /ask da 503."""
    try:
        assume = os.environ.get("MARKETPULSE_ASSUME_ROLE", "") == "1"
        return build_agent(aws_session(assume_role=assume))
    except MissingApiKeyError as e:
        logger.error("Agente no disponible: %s", e)
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agent = create_agent()
    yield


app = FastAPI(title="MarketPulse · agente text-to-SQL", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "agent_ready": app.state.agent is not None}


@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest) -> AskResponse:
    # `def` y no `async def`: Agent.ask es bloqueante (API de Claude y Athena) y FastAPI ejecuta
    # las funciones normales en un grupo de hilos, así una pregunta lenta no para a las demás
    agent = app.state.agent
    if agent is None:
        raise HTTPException(
            status_code=503, detail="Agente no configurado (falta ANTHROPIC_API_KEY)"
        )
    a = agent.ask(body.question.strip())
    return AskResponse(
        request_id=a.request_id,
        outcome=a.outcome,
        answer=a.answer,
        sql=a.sql,
        explanation=a.explanation,
        bytes_scanned=a.bytes_scanned,
        elapsed_ms=a.elapsed_ms,
        usage=Usage(**a.usage),
    )
