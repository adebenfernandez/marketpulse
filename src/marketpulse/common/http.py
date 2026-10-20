"""Cliente HTTP común para todas las fuentes: timeout, reintentos con espera exponencial y logging.

Cada cliente de API (Frankfurter, CoinGecko, Alpha Vantage) usa HttpClient.get_json() en lugar
de llamar a requests directamente, para que las tres fuentes se comporten igual ante fallos.
"""

import logging
import time
from collections.abc import Callable

import requests

logger = logging.getLogger(__name__)

# Errores pasajeros: merece la pena reintentar.
#   429 = demasiadas peticiones · 500/502/503/504 = el servidor (o un intermediario) ha fallado
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

# Nombres de parámetros/cabeceras que llevan claves de API: nunca se escriben en los logs
SENSITIVE_KEYS = frozenset({"apikey", "api_key", "x-cg-demo-api-key", "x_cg_demo_api_key"})


class HttpError(RuntimeError):
    """La petición ha fallado de forma definitiva (o se han agotado los reintentos)."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def redact(values: dict | None) -> dict:
    """Copia de params/cabeceras con las claves de API sustituidas por '***'."""
    return {k: ("***" if k.lower() in SENSITIVE_KEYS else v) for k, v in (values or {}).items()}


class HttpClient:
    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        max_backoff: float = 30.0,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.timeout = timeout  # segundos máximos esperando respuesta
        self.max_retries = max_retries  # reintentos DESPUÉS del primer intento
        self.backoff_base = backoff_base  # espera del primer reintento (luego x2, x4...)
        self.max_backoff = max_backoff  # tope de espera, por si la API pide algo desorbitado
        # Session reutiliza la conexión TCP entre peticiones al mismo servidor (más rápido).
        # Se puede inyectar una falsa en los tests: así no se llama a internet.
        self.session = session or requests.Session()
        # También inyectamos sleep: en los tests no queremos esperar segundos de verdad.
        self.sleep = sleep

    def _backoff(self, attempt: int, response: requests.Response | None) -> float:
        """Segundos a esperar antes del reintento número `attempt` (empieza en 0)."""
        # Si el servidor dice cuánto esperar (cabecera Retry-After en segundos), le hacemos caso
        if response is not None:
            retry_after = response.headers.get("Retry-After", "")
            if retry_after.isdigit():
                return min(float(retry_after), self.max_backoff)
        # Espera exponencial: 1 s, 2 s, 4 s, 8 s... con un tope
        return min(self.backoff_base * 2**attempt, self.max_backoff)

    def get_json(
        self, url: str, params: dict | None = None, headers: dict | None = None
    ) -> dict | list:
        """GET a `url` y devuelve el cuerpo JSON ya convertido a dict/list de Python."""
        safe_params = redact(params)
        total_attempts = self.max_retries + 1

        for attempt in range(total_attempts):
            start = time.perf_counter()
            response = None
            try:
                response = self.session.get(
                    url, params=params, headers=headers, timeout=self.timeout
                )
            except (requests.ConnectionError, requests.Timeout) as exc:
                # Fallo de red o timeout: pasajero, se reintenta.
                # Solo guardamos el TIPO de error: su mensaje incluye la URL con la clave.
                reason = type(exc).__name__
            except requests.RequestException as exc:
                # Cualquier otro error de requests (URL inválida, demasiadas redirecciones...):
                # no es pasajero. Lo convertimos en HttpError SIN el mensaje original, que
                # puede llevar la URL con la clave, y sin encadenarlo (`from None`).
                raise HttpError(f"GET {url} falló: {type(exc).__name__}") from None
            else:
                elapsed_ms = (time.perf_counter() - start) * 1000
                status = response.status_code
                logger.info(
                    "GET %s params=%s -> %s en %.0f ms", url, safe_params, status, elapsed_ms
                )
                if status < 400:
                    try:
                        return response.json()
                    except ValueError:
                        # 200 pero el cuerpo no es JSON: reintentar no lo arreglará
                        raise HttpError(
                            f"La respuesta de {url} no es JSON válido", status
                        ) from None
                if status not in RETRYABLE_STATUS:
                    # 400 (petición mal hecha), 401/403 (clave mala), 404 (no existe)...
                    # Son errores nuestros: reintentar daría el mismo resultado.
                    raise HttpError(f"GET {url} devolvió {status} (no se reintenta)", status)
                reason = f"HTTP {status}"

            if attempt < total_attempts - 1:
                wait = self._backoff(attempt, response)
                logger.warning(
                    "GET %s falló (%s). Reintento %d/%d en %.1f s",
                    url,
                    reason,
                    attempt + 1,
                    self.max_retries,
                    wait,
                )
                self.sleep(wait)

        # No se adjunta la excepción original de requests: su texto lleva la URL completa con
        # la clave de API y acabaría impresa en la traza del error. Solo damos el tipo de fallo.
        status_code = response.status_code if response is not None else None
        raise HttpError(
            f"GET {url} falló tras {total_attempts} intentos (último error: {reason})", status_code
        )
