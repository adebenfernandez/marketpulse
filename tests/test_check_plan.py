"""Tests de la guardia del despliegue (scripts/check_plan.py)."""

import importlib.util
import json
from pathlib import Path

import pytest

# scripts/ no es un paquete instalable: se carga el módulo por su ruta
_SPEC = importlib.util.spec_from_file_location(
    "check_plan", Path(__file__).resolve().parents[1] / "scripts" / "check_plan.py"
)
check_plan = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_plan)


def _plan(*changes):
    """Construye un plan mínimo con el formato de `terraform show -json`."""
    return {
        "resource_changes": [
            {"address": address, "change": {"actions": actions}} for address, actions in changes
        ]
    }


@pytest.mark.parametrize(
    "actions",
    [["no-op"], ["read"], ["create"], ["update"]],
)
def test_crear_modificar_o_nada_se_permite(actions):
    assert check_plan.dangerous_changes(_plan(("aws_lambda_function.this", actions))) == []


@pytest.mark.parametrize(
    "actions",
    [["delete"], ["delete", "create"], ["create", "delete"]],
)
def test_borrar_o_reemplazar_se_bloquea(actions):
    found = check_plan.dangerous_changes(_plan(("aws_s3_bucket.datalake", actions)))
    assert found == [f"aws_s3_bucket.datalake: {'+'.join(actions)}"]


def test_un_plan_sin_cambios_se_permite():
    assert check_plan.dangerous_changes({}) == []


def test_main_devuelve_1_si_hay_un_destroy(tmp_path, capsys):
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps(_plan(("aws_glue_catalog_table.daily_prices", ["delete"]))), encoding="utf-8"
    )
    assert check_plan.main(["check_plan.py", str(plan)]) == 1
    assert "aws_glue_catalog_table.daily_prices: delete" in capsys.readouterr().out


def test_main_devuelve_0_con_un_plan_seguro(tmp_path):
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(_plan(("aws_lambda_function.this", ["update"]))), encoding="utf-8")
    assert check_plan.main(["check_plan.py", str(plan)]) == 0
