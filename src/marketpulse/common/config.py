"""Lectura y validación de config/watchlist.yaml.

El YAML se convierte en objetos de Python inmutables (dataclasses con frozen=True).
Así el resto del código trabaja con atributos con nombre (watchlist.fx.base) en lugar de
diccionarios (data["fx"]["base"]), y un error de escritura en el YAML se detecta al arrancar,
no a mitad de la ingesta.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_WATCHLIST_PATH = Path("config/watchlist.yaml")


class ConfigError(ValueError):
    """El fichero de configuración no tiene el formato esperado."""


@dataclass(frozen=True)
class FxConfig:
    base: str
    quotes: tuple[str, ...]


@dataclass(frozen=True)
class CryptoAsset:
    symbol: str
    coingecko_id: str


@dataclass(frozen=True)
class CryptoConfig:
    vs_currency: str
    assets: tuple[CryptoAsset, ...]


@dataclass(frozen=True)
class StockAsset:
    symbol: str
    name: str


@dataclass(frozen=True)
class StocksConfig:
    assets: tuple[StockAsset, ...]


@dataclass(frozen=True)
class Watchlist:
    fx: FxConfig
    crypto: CryptoConfig
    stocks: StocksConfig


def _require(data: dict, key: str, section: str):
    """Devuelve data[key] o lanza un error que dice exactamente qué falta y dónde."""
    if not isinstance(data, dict) or key not in data:
        raise ConfigError(f"Falta la clave '{key}' en la sección '{section}' de la watchlist")
    return data[key]


def _non_empty_list(value, section: str) -> list:
    if not isinstance(value, list) or not value:
        raise ConfigError(f"'{section}' debe ser una lista con al menos un elemento")
    return value


def parse_watchlist(data: dict) -> Watchlist:
    """Valida un diccionario (el YAML ya leído) y lo convierte en un Watchlist."""
    fx = _require(data, "fx", "raíz")
    crypto = _require(data, "crypto", "raíz")
    stocks = _require(data, "stocks", "raíz")

    fx_quotes = _non_empty_list(_require(fx, "quotes", "fx"), "fx.quotes")
    crypto_assets = _non_empty_list(_require(crypto, "assets", "crypto"), "crypto.assets")
    stock_assets = _non_empty_list(_require(stocks, "assets", "stocks"), "stocks.assets")

    # Normalizamos mayúsculas/minúsculas aquí, una sola vez, para no repetirlo en cada cliente
    return Watchlist(
        fx=FxConfig(
            base=str(_require(fx, "base", "fx")).upper(),
            quotes=tuple(str(q).upper() for q in fx_quotes),
        ),
        crypto=CryptoConfig(
            vs_currency=str(_require(crypto, "vs_currency", "crypto")).lower(),
            assets=tuple(
                CryptoAsset(
                    symbol=str(_require(a, "symbol", "crypto.assets")).upper(),
                    coingecko_id=str(_require(a, "coingecko_id", "crypto.assets")).lower(),
                )
                for a in crypto_assets
            ),
        ),
        stocks=StocksConfig(
            assets=tuple(
                StockAsset(
                    symbol=str(_require(a, "symbol", "stocks.assets")).upper(),
                    name=str(a.get("name", "")),
                )
                for a in stock_assets
            ),
        ),
    )


def load_watchlist(path: Path | str = DEFAULT_WATCHLIST_PATH) -> Watchlist:
    """Lee el YAML del disco y lo valida."""
    with open(path, encoding="utf-8") as f:
        # safe_load solo crea tipos básicos (dict, list, str, números).
        # yaml.load sin más podría construir objetos arbitrarios de Python: riesgo de seguridad.
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ConfigError(f"{path} está vacío o no es un diccionario YAML")
    return parse_watchlist(data)
