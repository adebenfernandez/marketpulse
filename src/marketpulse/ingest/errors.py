"""Errores comunes de la ingesta."""


class UnexpectedResponseError(ValueError):
    """La API respondió con éxito (2xx) pero el contenido no tiene la forma esperada.

    Suele significar que la API ha cambiado su formato o que nos ha devuelto un aviso
    en lugar de datos. Es mejor parar y avisar que guardar basura en bronze.
    """


class MissingApiKeyError(RuntimeError):
    """Falta una clave de API obligatoria (variable de entorno no definida o vacía)."""


class PartialIngestError(RuntimeError):
    """Una fuente con varias peticiones (una por símbolo) ha fallado en alguna de ellas.

    Los símbolos que sí funcionaron ya están guardados; `failed` dice cuáles fallaron y por qué.
    """

    def __init__(self, source: str, failed: dict[str, str]):
        super().__init__(f"{source}: fallaron {len(failed)} símbolo(s): {failed}")
        self.source = source
        self.failed = failed
