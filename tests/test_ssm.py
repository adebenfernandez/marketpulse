"""Tests de la lectura de secretos de SSM con un Parameter Store FALSO (sin AWS)."""

import pytest

from marketpulse.common.ssm import MissingParameterError, get_parameters
from tests.fakes import FakeSSM


def test_lee_todo_en_una_llamada_descifrado_y_con_nuestros_nombres():
    fake = FakeSSM({"/mp/cg": "clave-cg", "/mp/av": "clave-av"})
    result = get_parameters(fake, {"COINGECKO_API_KEY": "/mp/cg", "ALPHAVANTAGE_API_KEY": "/mp/av"})
    assert result == {"COINGECKO_API_KEY": "clave-cg", "ALPHAVANTAGE_API_KEY": "clave-av"}
    assert len(fake.calls) == 1  # una sola petición para las dos claves
    assert fake.calls[0]["WithDecryption"] is True  # si no, devolvería el texto cifrado


def test_parametro_inexistente_da_error_claro_sin_valores():
    fake = FakeSSM({"/mp/cg": "clave-secreta"})
    with pytest.raises(MissingParameterError) as exc:
        get_parameters(fake, {"COINGECKO_API_KEY": "/mp/cg", "ALPHAVANTAGE_API_KEY": "/mp/nada"})
    assert "/mp/nada" in str(exc.value)
    assert "clave-secreta" not in str(exc.value)  # nunca un valor en un mensaje de error


def test_sin_parametros_no_llama_a_ssm():
    fake = FakeSSM({})
    assert get_parameters(fake, {}) == {}
    assert fake.calls == []
