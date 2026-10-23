"""Tests de la API (paso 7.9, D-037), llamando a los endpoints como funciones.

Se prueba la traducción HTTP ⇄ Agent sin servidor ni red. La prueba de verdad (HTTP real,
dentro de Docker, en localhost) es el criterio 3 de la fase y se hace con el contenedor.
"""

import importlib.util
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from api import main
from marketpulse.agent.agent import AgentAnswer

ROOT = Path(__file__).resolve().parents[1]

USAGE = {
    "model": "claude-haiku-5-5",
    "calls": 3,
    "input_tokens": 10,
    "output_tokens": 300,
    "cache_read_tokens": 5000,
    "cache_write_tokens": 2000,
    "cost_usd": 0.001,
}


class FakeAgent:
    def __init__(self):
        self.questions = []

    def ask(self, question):
        self.questions.append(question)
        return AgentAnswer(
            question=question,
            outcome="respondida",
            answer="SOL",
            sql="SELECT 1",
            explanation="x",
            request_id="abc",
            bytes_scanned=123,
            elapsed_ms=456,
            usage=USAGE,
        )


@pytest.fixture
def agent(monkeypatch):
    fake = FakeAgent()
    monkeypatch.setattr(main.app.state, "agent", fake, raising=False)
    return fake


def test_health(agent):
    assert main.health() == {"status": "ok", "agent_ready": True}


def test_ask_devuelve_la_respuesta_del_agente(agent):
    r = main.ask(main.AskRequest(question="  ¿Qué activo es más volátil?  "))
    assert agent.questions == ["¿Qué activo es más volátil?"]  # sin espacios alrededor
    assert (r.outcome, r.answer, r.sql, r.request_id) == ("respondida", "SOL", "SELECT 1", "abc")
    assert r.usage.cost_usd == 0.001


@pytest.mark.parametrize("question", ["", "ab", "x" * (main.MAX_QUESTION_CHARS + 1)])
def test_preguntas_vacias_o_demasiado_largas_se_rechazan(question):
    with pytest.raises(ValidationError):  # FastAPI lo convierte en un 422
        main.AskRequest(question=question)


def test_sin_agente_responde_503(monkeypatch):
    monkeypatch.setattr(main.app.state, "agent", None, raising=False)
    assert main.health()["agent_ready"] is False
    with pytest.raises(HTTPException) as info:
        main.ask(main.AskRequest(question="¿Qué tal BTC?"))
    assert info.value.status_code == 503


def test_el_bloqueo_de_la_imagen_cubre_las_dependencias_del_agente():
    # Si se añade una dependencia al agente y no se regenera config/agent-requirements.txt
    # (python scripts/lock_agent.py), la imagen fallaría al arrancar: mejor saberlo aquí
    spec = importlib.util.spec_from_file_location("lock_agent", ROOT / "scripts" / "lock_agent.py")
    lock_agent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lock_agent)
    needed = set(lock_agent.build_lambda.pinned_closure(lock_agent.AGENT_RUNTIME))
    locked = set(lock_agent.build_lambda.read_lock(lock_agent.LOCK_PATH))
    assert needed <= locked, f"Faltan en el bloqueo: {sorted(needed - locked)}"


def test_sin_clave_la_api_arranca_sin_agente(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("MARKETPULSE_ASSUME_ROLE", raising=False)
    assert main.create_agent() is None
