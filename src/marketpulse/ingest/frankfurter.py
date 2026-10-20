"""Cliente de Frankfurter: tipos de cambio de referencia del BCE (sin clave de API).

Documentación: https://frankfurter.dev/ (API v2; la v1 está obsoleta).
Pedimos solo el proveedor ECB (Banco Central Europeo): sin `providers`, Frankfurter devuelve
una media de varios bancos centrales, que no es lo que dice el informe del proyecto.
Condiciones del BCE: uso libre citando al BCE como fuente y sin alterar los datos.

Respuesta (una fila por divisa; `date` es el último día publicado por el BCE, que en fines
de semana y festivos es anterior al día de la ejecución):
    [{"date": "2026-10-20", "base": "EUR", "quote": "GBP", "rate": 0.84028}, ...]
"""

import logging
from datetime import date
from pathlib import Path

from marketpulse.common.config import FxConfig
from marketpulse.common.http import HttpClient
from marketpulse.common.storage import DEFAULT_DATA_ROOT, write_bronze
from marketpulse.ingest.errors import UnexpectedResponseError

logger = logging.getLogger(__name__)

SOURCE = "frankfurter"
RATES_URL = "https://api.frankfurter.dev/v2/rates"
PROVIDER = "ECB"
REQUIRED_FIELDS = ("date", "base", "quote", "rate")


def fetch_rates(client: HttpClient, fx: FxConfig) -> list[dict]:
    """Pide los últimos tipos publicados de `fx.base` frente a cada divisa de `fx.quotes`."""
    params = {
        "base": fx.base,
        "quotes": ",".join(fx.quotes),  # una sola petición para todas las divisas: "USD,GBP"
        "providers": PROVIDER,
    }
    data = client.get_json(RATES_URL, params=params)

    # Comprobación mínima de forma: si la API cambia de formato, paramos aquí.
    # (Las comprobaciones de calidad de verdad —rangos, nulos, frescura— son de la Fase 2.)
    if not isinstance(data, list) or not data:
        raise UnexpectedResponseError(
            f"Frankfurter: se esperaba una lista no vacía, llegó {data!r:.200}"
        )
    for row in data:
        if not isinstance(row, dict) or any(field not in row for field in REQUIRED_FIELDS):
            raise UnexpectedResponseError(f"Frankfurter: fila con formato inesperado: {row!r:.200}")

    missing = set(fx.quotes) - {row["quote"] for row in data}
    if missing:
        # No es motivo para parar (las demás divisas sí llegaron), pero tiene que quedar registrado
        logger.warning("Frankfurter no devolvió estas divisas: %s", sorted(missing))
    return data


def ingest(
    client: HttpClient, fx: FxConfig, dt: date | None = None, root: Path = DEFAULT_DATA_ROOT
) -> Path:
    """Descarga los tipos y los guarda en bronze. Devuelve la ruta del fichero escrito."""
    data = fetch_rates(client, fx)
    path = write_bronze(SOURCE, data, dt=dt, root=root)
    logger.info("Frankfurter: %d tipos guardados en %s", len(data), path)
    return path
