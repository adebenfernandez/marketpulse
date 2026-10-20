"""Tests del cliente HTTP. Ninguno llama a internet: la sesión de requests es un mock."""

import logging
from unittest.mock import MagicMock

import pytest
import requests

from marketpulse.common.http import HttpClient, HttpError, redact


def fake_response(status: int, body=None, headers: dict | None = None) -> MagicMock:
    """Crea una respuesta falsa que se comporta como requests.Response en lo que usamos."""
    response = MagicMock()
    response.status_code = status
    response.headers = headers or {}
    response.json.return_value = body
    return response


def make_client(*results) -> tuple[HttpClient, MagicMock, list[float]]:
    """Cliente cuya sesión devuelve `results` en orden (respuestas o excepciones).

    Devuelve también la sesión falsa (para contar llamadas) y la lista de esperas registradas.
    """
    session = MagicMock()
    session.get.side_effect = list(results)  # cada llamada a get() saca el siguiente elemento
    waits: list[float] = []
    client = HttpClient(max_retries=3, backoff_base=1.0, session=session, sleep=waits.append)
    return client, session, waits


def test_respuesta_correcta_devuelve_el_json():
    client, session, waits = make_client(fake_response(200, {"rates": {"USD": 1.08}}))
    assert client.get_json("https://api.ejemplo.com/latest") == {"rates": {"USD": 1.08}}
    assert session.get.call_count == 1
    assert waits == []  # no hubo que esperar


def test_pasa_el_timeout_a_requests():
    client, session, _ = make_client(fake_response(200, {}))
    client.get_json("https://api.ejemplo.com")
    assert session.get.call_args.kwargs["timeout"] == 10.0


def test_error_503_se_reintenta_y_luego_funciona():
    client, session, waits = make_client(fake_response(503), fake_response(200, {"ok": True}))
    assert client.get_json("https://api.ejemplo.com") == {"ok": True}
    assert session.get.call_count == 2
    assert waits == [1.0]


def test_espera_exponencial_y_se_rinde_al_agotar_reintentos():
    client, session, waits = make_client(*[fake_response(500)] * 4)
    with pytest.raises(HttpError, match="4 intentos") as excinfo:
        client.get_json("https://api.ejemplo.com")
    assert session.get.call_count == 4  # 1 intento + 3 reintentos
    assert waits == [1.0, 2.0, 4.0]  # 1 s, 2 s, 4 s
    assert excinfo.value.status_code == 500


def test_429_respeta_la_cabecera_retry_after():
    client, _, waits = make_client(
        fake_response(429, headers={"Retry-After": "7"}), fake_response(200, {})
    )
    client.get_json("https://api.ejemplo.com")
    assert waits == [7.0]


def test_404_no_se_reintenta():
    client, session, waits = make_client(fake_response(404))
    with pytest.raises(HttpError, match="404") as excinfo:
        client.get_json("https://api.ejemplo.com/no-existe")
    assert session.get.call_count == 1
    assert waits == []
    assert excinfo.value.status_code == 404


def test_timeout_de_red_se_reintenta():
    client, session, waits = make_client(requests.Timeout("lento"), fake_response(200, {"ok": 1}))
    assert client.get_json("https://api.ejemplo.com") == {"ok": 1}
    assert waits == [1.0]


def test_cuerpo_que_no_es_json_da_error_sin_reintentar():
    response = fake_response(200)
    response.json.side_effect = ValueError("no es JSON")
    client, session, _ = make_client(response)
    with pytest.raises(HttpError, match="no es JSON"):
        client.get_json("https://api.ejemplo.com")
    assert session.get.call_count == 1


def test_otro_error_de_requests_no_se_reintenta_ni_filtra_la_clave():
    # requests incluye la URL completa (con la clave) en el texto de sus excepciones
    error = requests.TooManyRedirects("https://api.ejemplo.com/?apikey=SECRETO123")
    client, session, waits = make_client(error)
    with pytest.raises(HttpError) as excinfo:
        client.get_json("https://api.ejemplo.com", params={"apikey": "SECRETO123"})
    assert session.get.call_count == 1 and waits == []
    assert "SECRETO123" not in str(excinfo.value)
    assert excinfo.value.__cause__ is None and excinfo.value.__suppress_context__  # sin encadenar


def test_la_clave_de_api_no_aparece_en_los_logs(caplog):
    # caplog es una herramienta de pytest que captura lo que se escribe en el log
    caplog.set_level(logging.INFO)
    client, _, _ = make_client(fake_response(503), fake_response(200, {}))
    client.get_json("https://api.ejemplo.com", params={"symbol": "SPY", "apikey": "SECRETO123"})
    assert "SECRETO123" not in caplog.text
    assert "SPY" in caplog.text  # el resto de parámetros sí se ven


def test_redact_oculta_solo_las_claves_sensibles():
    assert redact({"apikey": "x", "symbol": "SPY"}) == {"apikey": "***", "symbol": "SPY"}
    assert redact(None) == {}
