"""Cuenta de tokens y coste de cada pregunta al agente (D-031).

Una pregunta hace varias llamadas a la API de Claude (una por vuelta del bucle agéntico), y cada
respuesta trae su `usage`. Aquí se suman todas y se calcula el coste en USD con los precios
oficiales del 2026-10-22 (D-029). El coste se calcula llamada a llamada porque en Haiku 5.5 el
precio depende del tamaño del prompt de CADA llamada (más de 100.000 tokens → tarifa más cara).

Si cambian los precios, se cambia la tabla PRICES (y la fecha de este comentario).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Price:
    """USD por millón de tokens."""

    input: float
    output: float
    cache_read: float
    cache_write: float  # escritura en caché de 5 minutos


@dataclass(frozen=True)
class ModelPricing:
    standard: Price
    long_prompt: Price | None = None  # tarifa para prompts de más de `long_prompt_from` tokens
    long_prompt_from: int = 100_000


PRICES: dict[str, ModelPricing] = {
    "claude-haiku-5-5": ModelPricing(
        standard=Price(input=0.10, output=0.50, cache_read=0.01, cache_write=0.125),
        long_prompt=Price(input=0.50, output=2.50, cache_read=0.05, cache_write=0.625),
    ),
    "claude-sonnet-5-5": ModelPricing(
        standard=Price(input=2.00, output=10.00, cache_read=0.10, cache_write=2.50),
    ),
}

MILLION = 1_000_000


class UnknownModelError(KeyError):
    """No tenemos el precio de ese modelo: mejor fallar que apuntar un coste de 0."""


@dataclass
class TokenUsage:
    """Suma de los `usage` de todas las llamadas de una pregunta."""

    model: str
    calls: int = 0
    input_tokens: int = 0  # entrada sin caché (precio completo)
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0

    def __post_init__(self) -> None:
        if self.model not in PRICES:
            raise UnknownModelError(f"sin precio para el modelo {self.model!r}; añádelo a PRICES")

    def add(self, usage) -> None:
        """Suma el `response.usage` de una llamada (objeto del SDK o algo con los mismos campos)."""
        inp = usage.input_tokens or 0
        out = usage.output_tokens or 0
        read = getattr(usage, "cache_read_input_tokens", None) or 0
        write = getattr(usage, "cache_creation_input_tokens", None) or 0

        pricing = PRICES[self.model]
        prompt_tokens = inp + read + write  # la API mide el prompt con las tres partes
        use_long = pricing.long_prompt is not None and prompt_tokens > pricing.long_prompt_from
        price = pricing.long_prompt if use_long else pricing.standard

        self.calls += 1
        self.input_tokens += inp
        self.output_tokens += out
        self.cache_read_tokens += read
        self.cache_write_tokens += write
        self.cost_usd += (
            inp * price.input
            + out * price.output
            + read * price.cache_read
            + write * price.cache_write
        ) / MILLION

    def as_dict(self) -> dict:
        return {
            "model": self.model,
            "calls": self.calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "cost_usd": round(self.cost_usd, 6),
        }
