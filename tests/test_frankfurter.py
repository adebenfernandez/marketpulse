"""Tests del cliente de Frankfurter. El HttpClient es un mock: no se llama a la API real."""

import json
import logging
from datetime import date
from unittest.mock import MagicMock

import pytest

from marketpulse.common.config import FxConfig
from marketpulse.ingest import frankfurter
from marketpulse.ingest.errors import UnexpectedResponseError

FX = FxConfig(base="EUR", quotes=("USD", "GBP"))
DIA = date(2026, 10, 20)

# Copia de una respuesta real de la API (20/10/2026), para que el test se parezca a la realidad
RESPUESTA_REAL = [
    {"date": "2026-10-20", "base": "EUR", "quote": "GBP", "rate": 0.84028},
    {"date": "2026-10-20", "base": "EUR", "quote": "USD", "rate": 1.1215},
]


def mock_client(respuesta) -> MagicMock:
    client = MagicMock()
    client.get_json.return_value = respuesta
    return client


def test_pide_las_divisas_de_la_watchlist_al_bce():
    client = mock_client(RESPUESTA_REAL)
    frankfurter.fetch_rates(client, FX)
    client.get_json.assert_called_once_with(
        "https://api.frankfurter.dev/v2/rates",
        params={"base": "EUR", "quotes": "USD,GBP", "providers": "ECB"},
    )


def test_ingest_guarda_la_respuesta_en_su_particion(tmp_path):
    path = frankfurter.ingest(mock_client(RESPUESTA_REAL), FX, dt=DIA, root=tmp_path)
    assert path == tmp_path / "bronze" / "source=frankfurter" / "dt=2026-10-20" / "frankfurter.json"
    assert json.loads(path.read_text(encoding="utf-8")) == RESPUESTA_REAL


@pytest.mark.parametrize(
    "respuesta",
    [
        [],  # lista vacía
        {"rates": {"USD": 1.1}},  # formato antiguo (v1): un diccionario, no una lista
        [{"base": "EUR", "quote": "USD"}],  # falta "rate" y "date"
    ],
)
def test_respuesta_con_forma_inesperada_da_error_y_no_escribe(tmp_path, respuesta):
    with pytest.raises(UnexpectedResponseError):
        frankfurter.ingest(mock_client(respuesta), FX, dt=DIA, root=tmp_path)
    assert not (tmp_path / "bronze").exists()


def test_avisa_si_falta_una_divisa(caplog):
    caplog.set_level(logging.WARNING)
    solo_usd = [RESPUESTA_REAL[1]]
    assert frankfurter.fetch_rates(mock_client(solo_usd), FX) == solo_usd
    assert "GBP" in caplog.text
