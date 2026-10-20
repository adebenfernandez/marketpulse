"""Tests del orquestador. Las tres fuentes se sustituyen por funciones falsas con monkeypatch."""

import logging
from datetime import date
from unittest.mock import MagicMock

import pytest

from marketpulse.common.config import load_watchlist
from marketpulse.ingest import alphavantage, coingecko, frankfurter, run
from marketpulse.ingest.errors import MissingApiKeyError

WATCHLIST = load_watchlist()
DIA = date(2026, 10, 20)


@pytest.fixture
def calls(monkeypatch) -> dict:
    """Sustituye el ingest() de cada fuente por uno falso que apunta con qué se le llamó."""
    registro: dict = {}

    def fake(name):
        def _ingest(client, cfg, *args, **kwargs):
            registro[name] = {"args": args, "kwargs": kwargs}

        return _ingest

    monkeypatch.setattr(frankfurter, "ingest", fake("frankfurter"))
    monkeypatch.setattr(coingecko, "ingest", fake("coingecko"))
    monkeypatch.setattr(alphavantage, "ingest", fake("alphavantage"))
    return registro


def test_todas_bien(calls, tmp_path):
    results = run.run_all(WATCHLIST, MagicMock(), env={}, dt=DIA, root=tmp_path)
    assert results == {"frankfurter": None, "coingecko": None, "alphavantage": None}
    assert set(calls) == {"frankfurter", "coingecko", "alphavantage"}


def test_pasa_las_claves_del_entorno_y_la_misma_fecha_a_todas(calls, tmp_path):
    env = {"COINGECKO_API_KEY": "cg-prueba", "ALPHAVANTAGE_API_KEY": "av-prueba"}
    run.run_all(WATCHLIST, MagicMock(), env=env, dt=DIA, root=tmp_path)
    assert calls["coingecko"]["args"] == ("cg-prueba",)
    assert calls["alphavantage"]["args"] == ("av-prueba",)
    assert all(c["kwargs"]["dt"] == DIA for c in calls.values())


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [(None, None), ("", None), ("   ", None), ("  clave-prueba \n", "clave-prueba")],
)
def test_get_secret_trata_vacio_y_espacios_como_sin_clave(valor, esperado):
    env = {} if valor is None else {"X": valor}
    assert run.get_secret(env, "X") == esperado


def test_una_clave_de_solo_espacios_llega_como_none(calls, tmp_path):
    run.run_all(WATCHLIST, MagicMock(), env={"ALPHAVANTAGE_API_KEY": " "}, dt=DIA, root=tmp_path)
    assert calls["alphavantage"]["args"] == (None,)


def test_si_una_fuente_falla_las_demas_se_ejecutan(calls, monkeypatch, tmp_path, caplog):
    def falla(*args, **kwargs):
        raise MissingApiKeyError("Alpha Vantage necesita la variable ALPHAVANTAGE_API_KEY")

    monkeypatch.setattr(alphavantage, "ingest", falla)
    with caplog.at_level(logging.ERROR):
        results = run.run_all(WATCHLIST, MagicMock(), env={}, dt=DIA, root=tmp_path)

    assert results["frankfurter"] is None and results["coingecko"] is None
    assert results["alphavantage"].startswith("MissingApiKeyError")
    assert "alphavantage" in caplog.text


def test_main_devuelve_0_si_todo_va_bien_y_1_si_algo_falla(monkeypatch):
    # No queremos que el test lea tu .env real ni que llame a internet
    monkeypatch.setattr(run, "load_dotenv", lambda: None)
    monkeypatch.setattr(run, "run_all", lambda *a, **k: {"frankfurter": None})
    assert run.main(env={}) == 0

    monkeypatch.setattr(run, "run_all", lambda *a, **k: {"frankfurter": None, "x": "Error"})
    assert run.main(env={}) == 1
