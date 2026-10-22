"""Tests de la cuenta de tokens y coste (paso 7.3, D-031). Las cuentas se pueden hacer a mano."""

from types import SimpleNamespace

import pytest

from marketpulse.agent.usage import TokenUsage, UnknownModelError


def fake_usage(inp=0, out=0, read=None, write=None):
    """Imita `response.usage` del SDK. Los campos de caché pueden venir a None."""
    return SimpleNamespace(
        input_tokens=inp,
        output_tokens=out,
        cache_read_input_tokens=read,
        cache_creation_input_tokens=write,
    )


def test_una_llamada_de_haiku():
    u = TokenUsage("claude-haiku-5-5")
    u.add(fake_usage(inp=10_000, out=1_000))
    # 10.000 × 0,10 + 1.000 × 0,50 = 1.000 + 500 = 1.500 USD por millón → 0,0015 USD
    assert u.cost_usd == pytest.approx(0.0015)
    assert u.calls == 1


def test_se_suman_varias_llamadas():
    u = TokenUsage("claude-haiku-5-5")
    for _ in range(4):
        u.add(fake_usage(inp=5_000, out=300))
    assert (u.calls, u.input_tokens, u.output_tokens) == (4, 20_000, 1_200)
    assert u.cost_usd == pytest.approx((20_000 * 0.10 + 1_200 * 0.50) / 1e6)


def test_cache_con_su_precio():
    u = TokenUsage("claude-haiku-5-5")
    u.add(fake_usage(inp=1_000, out=0, read=8_000, write=2_000))
    # 1.000 × 0,10 + 8.000 × 0,01 + 2.000 × 0,125 = 100 + 80 + 250 = 430 → 0,00043 USD
    assert u.cost_usd == pytest.approx(0.00043)
    assert (u.cache_read_tokens, u.cache_write_tokens) == (8_000, 2_000)


def test_prompt_largo_de_haiku_usa_la_tarifa_cara():
    u = TokenUsage("claude-haiku-5-5")
    # 20.000 sin caché + 90.000 leídos de caché = 110.000 > 100.000 → tarifa larga en TODO
    u.add(fake_usage(inp=20_000, out=1_000, read=90_000))
    esperado = (20_000 * 0.50 + 1_000 * 2.50 + 90_000 * 0.05) / 1e6
    assert u.cost_usd == pytest.approx(esperado)


def test_el_umbral_se_mira_llamada_a_llamada():
    u = TokenUsage("claude-haiku-5-5")
    u.add(fake_usage(inp=60_000))
    u.add(fake_usage(inp=60_000))  # juntas suman 120.000, pero cada una es corta
    assert u.cost_usd == pytest.approx(120_000 * 0.10 / 1e6)


def test_sonnet_no_tiene_tarifa_larga():
    u = TokenUsage("claude-sonnet-5-5")
    u.add(fake_usage(inp=200_000, out=1_000))
    assert u.cost_usd == pytest.approx((200_000 * 2.00 + 1_000 * 10.00) / 1e6)


def test_modelo_sin_precio_falla():
    with pytest.raises(UnknownModelError):
        TokenUsage("claude-modelo-inventado")


def test_as_dict_redondea_el_coste():
    u = TokenUsage("claude-haiku-5-5")
    u.add(fake_usage(inp=1, out=1))
    d = u.as_dict()
    assert d["cost_usd"] == round(0.6 / 1e6, 6)
    assert set(d) >= {"model", "calls", "input_tokens", "output_tokens", "cost_usd"}
