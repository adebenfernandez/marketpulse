"""Tests de la escritura bronze. Usan tmp_path: una carpeta temporal que pytest crea y borra."""

import json
from datetime import UTC, date, datetime

import pytest

from marketpulse.common import storage
from marketpulse.common.storage import bronze_path, utc_today, write_bronze

DIA = date(2026, 10, 20)


def test_ruta_con_particiones_estilo_hive(tmp_path):
    path = bronze_path("alphavantage", DIA, name="SPY", root=tmp_path)
    expected = tmp_path / "bronze" / "source=alphavantage" / "dt=2026-10-20" / "SPY.json"
    assert path == expected


def test_sin_nombre_el_fichero_se_llama_como_la_fuente(tmp_path):
    assert bronze_path("frankfurter", DIA, root=tmp_path).name == "frankfurter.json"


def test_guarda_el_json_original_sin_cambios(tmp_path):
    payload = {"base": "EUR", "rates": {"USD": 1.0812, "GBP": 0.8345}}
    path = write_bronze("frankfurter", payload, dt=DIA, root=tmp_path)
    assert json.loads(path.read_text(encoding="utf-8")) == payload


def test_dos_ejecuciones_el_mismo_dia_no_duplican(tmp_path):
    write_bronze("frankfurter", {"version": 1}, dt=DIA, root=tmp_path)
    write_bronze("frankfurter", {"version": 2}, dt=DIA, root=tmp_path)

    files = list((tmp_path / "bronze").rglob("*"))
    json_files = [f for f in files if f.is_file()]
    assert len(json_files) == 1  # un solo fichero, no dos
    assert json.loads(json_files[0].read_text(encoding="utf-8")) == {"version": 2}  # el último


def test_dias_distintos_van_a_particiones_distintas(tmp_path):
    write_bronze("frankfurter", {}, dt=date(2026, 10, 20), root=tmp_path)
    write_bronze("frankfurter", {}, dt=date(2026, 10, 21), root=tmp_path)
    partitions = sorted(p.name for p in (tmp_path / "bronze" / "source=frankfurter").iterdir())
    assert partitions == ["dt=2026-10-20", "dt=2026-10-21"]


def test_si_falla_la_escritura_queda_el_fichero_anterior_y_no_hay_temporales(tmp_path, monkeypatch):
    path = write_bronze("frankfurter", {"version": 1}, dt=DIA, root=tmp_path)

    def replace_que_falla(src, dst):
        raise OSError("disco lleno (simulado)")

    # monkeypatch cambia os.replace SOLO durante este test (luego lo restaura)
    monkeypatch.setattr(storage.os, "replace", replace_que_falla)
    with pytest.raises(OSError, match="disco lleno"):
        write_bronze("frankfurter", {"version": 2}, dt=DIA, root=tmp_path)

    assert json.loads(path.read_text(encoding="utf-8")) == {"version": 1}  # intacto
    assert list(path.parent.glob("*.tmp")) == []  # temporal borrado


def test_payload_no_serializable_no_escribe_nada(tmp_path):
    with pytest.raises(TypeError):
        write_bronze("frankfurter", {"fecha": object()}, dt=DIA, root=tmp_path)
    assert not bronze_path("frankfurter", DIA, root=tmp_path).exists()


@pytest.mark.parametrize("bad", ["../windows", "a/b", r"a\b", "con espacio", "SPY.json"])
def test_rechaza_nombres_peligrosos(tmp_path, bad):
    # parametrize ejecuta este test una vez por cada valor de la lista
    with pytest.raises(ValueError):
        bronze_path(bad, DIA, root=tmp_path)  # como fuente
    with pytest.raises(ValueError):
        bronze_path("frankfurter", DIA, name=bad, root=tmp_path)  # como nombre de fichero


def test_utc_today_es_la_fecha_utc():
    assert utc_today() == datetime.now(UTC).date()
