"""Tests del empaquetado reproducible de las Lambdas (scripts/build_lambda.py, paso 6.7)."""

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "build_lambda", Path(__file__).resolve().parents[1] / "scripts" / "build_lambda.py"
)
build_lambda = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(build_lambda)


def test_el_agente_no_va_al_zip_de_lambda(tmp_path):
    names = [arcname for _, arcname in build_lambda.files_to_package(tmp_path)]
    assert "marketpulse/ingest/handler.py" in names
    assert "marketpulse/common/athena.py" in names
    assert not [n for n in names if n.startswith("marketpulse/agent/")]


def test_nuestro_codigo_se_empaqueta_con_finales_lf(tmp_path):
    fichero = tmp_path / "x.py"
    fichero.write_bytes(b"a = 1\r\nb = 2\r\n")  # como lo entrega Git en Windows
    assert build_lambda.packaged_bytes(fichero, "marketpulse/x.py") == b"a = 1\nb = 2\n"


def test_las_dependencias_no_se_tocan(tmp_path):
    fichero = tmp_path / "cacert.pem"
    fichero.write_bytes(b"linea\r\n")
    assert build_lambda.packaged_bytes(fichero, "certifi/cacert.pem") == b"linea\r\n"


def test_el_bloqueo_se_escribe_y_se_lee_igual(tmp_path):
    lock = tmp_path / "lock.txt"
    build_lambda.write_lock({"requests": "2.34.2", "idna": "3.20"}, lock)
    assert build_lambda.read_lock(lock) == {"idna": "3.20", "requests": "2.34.2"}


def test_el_bloqueo_del_repo_cubre_las_dependencias_del_venv():
    # Si alguien cambia las dependencias en pyproject.toml y no regenera el bloqueo, falla aquí
    venv = build_lambda.pinned_closure(build_lambda.runtime_requirements())
    build_lambda.check_lock_covers(build_lambda.read_lock(), set(venv))


def test_un_bloqueo_incompleto_para_con_un_mensaje_claro():
    with pytest.raises(SystemExit, match="--update-lock"):
        build_lambda.check_lock_covers({"requests": "2.34.2"}, {"requests", "idna"})
