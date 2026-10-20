"""Comprobaciones genéricas: cada una recibe una tabla y devuelve un CheckResult.

No saben nada de divisas ni de bolsa: solo de columnas. Las reglas concretas de MarketPulse
(qué columna, qué rango, qué antigüedad) están en rules.py. Separarlo permite reutilizar las
mismas comprobaciones con cualquier tabla y probarlas por separado.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

ERROR = "error"  # el dato es inaceptable: se para el proceso y no se publica nada
WARNING = "warning"  # sospechoso pero posible (p. ej. un salto grande): se avisa y se sigue

MAX_EXAMPLES = 5  # filas de ejemplo en el informe, para no llenar el log


@dataclass(frozen=True)
class CheckResult:
    table: str
    check: str  # descripción legible: "not_null(price)", "freshness(BTC)"...
    severity: str
    failed: int  # nº de filas (o activos) que incumplen la regla; 0 = pasa
    examples: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.failed == 0


def _result(table, check, severity, bad_rows: pd.DataFrame) -> CheckResult:
    examples = [str(r) for r in bad_rows.head(MAX_EXAMPLES).to_dict("records")]
    return CheckResult(table, check, severity, len(bad_rows), examples)


def not_null(df: pd.DataFrame, table: str, columns: Iterable[str]) -> list[CheckResult]:
    """Ninguna de `columns` puede estar vacía (None/NaN)."""
    return [_result(table, f"not_null({c})", ERROR, df[df[c].isna()]) for c in columns]


def unique(df: pd.DataFrame, table: str, key: list[str]) -> CheckResult:
    """No puede haber dos filas con la misma clave."""
    bad = df[df.duplicated(subset=key, keep=False)]  # keep=False: marca TODAS las repetidas
    return _result(table, f"unique({', '.join(key)})", ERROR, bad)


def in_range(
    df: pd.DataFrame,
    table: str,
    column: str,
    min_value: float | None = None,
    max_value: float | None = None,
    min_inclusive: bool = True,
) -> CheckResult:
    """`column` debe estar entre `min_value` y `max_value` (los nulos los vigila not_null)."""
    values = df[column]
    ok = pd.Series(True, index=df.index)
    if min_value is not None:
        ok &= values >= min_value if min_inclusive else values > min_value
    if max_value is not None:
        ok &= values <= max_value
    bad = df[~ok & values.notna()]
    op = ">=" if min_inclusive else ">"
    desc = " y ".join(
        part
        for part in (
            f"{column} {op} {min_value}" if min_value is not None else "",
            f"{column} <= {max_value}" if max_value is not None else "",
        )
        if part
    )
    return _result(table, f"range({desc})", ERROR, bad)


def rule(df: pd.DataFrame, table: str, name: str, ok: pd.Series) -> CheckResult:
    """Regla libre entre columnas: `ok` dice, fila a fila, si se cumple (p. ej. high >= low)."""
    return _result(table, f"rule({name})", ERROR, df[~ok])


def accepted_values(df: pd.DataFrame, table: str, column: str, allowed: set[str]) -> CheckResult:
    """`column` solo puede tomar valores de `allowed`."""
    bad = df[~df[column].isin(allowed)]
    return _result(table, f"accepted_values({column} in {sorted(allowed)})", ERROR, bad)


def freshness(
    df: pd.DataFrame,
    table: str,
    expected: dict[str, int],
    today: date,
    group_col: str = "asset",
    date_col: str = "date",
) -> list[CheckResult]:
    """Cada grupo esperado debe tener un dato de hace como mucho N días.

    `expected` = {activo: días máximos}. Un activo esperado SIN ningún dato también falla:
    así se detecta "añadí un activo a la watchlist y nunca se ha llegado a descargar".
    """
    last = df.groupby(group_col)[date_col].max()
    results = []
    for name, max_age in sorted(expected.items()):
        last_date = last.get(name)
        age = None if last_date is None else (today - last_date).days
        bad = age is None or age > max_age
        examples = (
            [f"{name}: último dato {last_date} ({age} días; máximo {max_age})"] if bad else []
        )
        results.append(CheckResult(table, f"freshness({name})", ERROR, int(bad), examples))
    return results


def max_daily_jump(
    df: pd.DataFrame,
    table: str,
    max_jump: float,
    group_col: str = "asset",
    value_col: str = "price",
    date_col: str = "date",
) -> CheckResult:
    """Avisa (WARNING) si un valor cambia más de `max_jump` (0.5 = 50 %) respecto al dato anterior
    del mismo grupo. Un salto así suele ser un error, pero puede ser real (un desplome, un split).
    """
    ordered = df.sort_values([group_col, date_col])
    previous = ordered.groupby(group_col)[value_col].shift(1)  # el dato anterior DEL MISMO activo
    change = (ordered[value_col] / previous - 1).abs()
    # Primero añadir columnas y DESPUÉS filtrar: al revés, si no hay saltos, pandas asigna las
    # columnas a una tabla vacía adoptando su índice y fabrica filas llenas de NaN
    annotated = ordered.assign(previous=previous, change=change.round(3))
    bad = annotated[change > max_jump]
    return _result(table, f"max_daily_jump({value_col}, {max_jump:.0%})", WARNING, bad)
