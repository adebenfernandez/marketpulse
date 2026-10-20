"""Lectura de secretos (claves de API) desde AWS SSM Parameter Store.

En local las claves vienen de .env. En Lambda no hay .env: cada clave es un parámetro SecureString
(cifrado con KMS) y la función lo lee al ejecutarse. Así el secreto nunca pasa por Terraform (su
state lo guarda todo en texto plano) ni por la configuración visible de la Lambda.
"""

from collections.abc import Mapping


class MissingParameterError(RuntimeError):
    """Algún parámetro pedido no existe en SSM (o el rol no tiene permiso para verlo)."""


def get_parameters(client, names: Mapping[str, str]) -> dict[str, str]:
    """Lee varios parámetros de una vez y los devuelve descifrados.

    `names` traduce "nombre de la clave en el programa" -> "nombre del parámetro en SSM", p. ej.
    {"COINGECKO_API_KEY": "/marketpulse/coingecko_api_key"}. Devuelve {"COINGECKO_API_KEY": "..."}.
    """
    if not names:
        return {}
    # get_parameters (en plural) pide hasta 10 parámetros en UNA sola llamada a la API.
    # WithDecryption=True: SSM descifra el SecureString con KMS antes de devolverlo.
    response = client.get_parameters(Names=sorted(set(names.values())), WithDecryption=True)

    # Si falta alguno, SSM no lanza error: lo devuelve en "InvalidParameters". Lo convertimos en
    # un error claro. El mensaje lleva solo NOMBRES de parámetros, nunca valores.
    missing = response.get("InvalidParameters", [])
    if missing:
        raise MissingParameterError(f"Parámetros de SSM no encontrados: {sorted(missing)}")

    values = {p["Name"]: p["Value"] for p in response["Parameters"]}
    return {key: values[param] for key, param in names.items()}
