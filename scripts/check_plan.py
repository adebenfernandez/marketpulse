"""Guardia del despliegue automático: falla si el plan de Terraform destruye o reemplaza algo.

Uso (en buildspec.yml, después de `terraform plan -out=tfplan`):
    terraform show -json tfplan > plan.json
    python scripts/check_plan.py plan.json

Por qué: CodeBuild aplica el plan sin que nadie lo mire (D-027). Crear o modificar recursos es
normal en un despliegue; borrar o recrear uno (un bucket, una tabla, un rol) casi nunca lo es y
puede perder datos. Ante cualquier "delete" (incluido un replace, que es delete + create) el build
se para con código 1 y un humano revisa y aplica a mano.

Lee el formato JSON oficial de Terraform: cada elemento de `resource_changes` trae
`change.actions`, una lista como ["create"], ["update"], ["delete"] o ["delete", "create"].
"""

import json
import sys
from pathlib import Path

# Acciones que paran el despliegue. "delete" cubre también los replace (["delete", "create"] o
# ["create", "delete"] con create_before_destroy)
FORBIDDEN_ACTIONS = {"delete"}


def dangerous_changes(plan: dict) -> list[str]:
    """Devuelve una línea por cada recurso que el plan borraría o reemplazaría."""
    found = []
    for change in plan.get("resource_changes", []):
        actions = change.get("change", {}).get("actions", [])
        if FORBIDDEN_ACTIONS.intersection(actions):
            found.append(f"{change.get('address', '?')}: {'+'.join(actions)}")
    return found


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Uso: python scripts/check_plan.py plan.json", file=sys.stderr)
        return 2
    plan = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    found = dangerous_changes(plan)
    if found:
        print("GUARDIA: el plan borra o reemplaza recursos. No se aplica automáticamente:")
        for line in found:
            print(f"  - {line}")
        print("Revísalo y, si es intencionado, aplícalo a mano (README, 'Desplegar desde cero').")
        return 1
    print("GUARDIA: el plan no borra ni reemplaza nada. Se puede aplicar.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
