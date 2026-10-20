"""Tests de los handlers de Lambda con S3 y SSM FALSOS: sin AWS, sin internet, sin credenciales.

La ingesta y la transformación de verdad ya tienen sus tests. Aquí se comprueba lo que añade el
handler: leer secretos, mover ficheros entre /tmp y S3, y LANZAR un error cuando algo falla.
"""

from datetime import date

import pytest

from marketpulse.common.lambda_runtime import JobFailedError
from marketpulse.common.storage import write_bronze
from marketpulse.ingest import handler as ingest_handler
from marketpulse.transform import handler as transform_handler
from tests.fakes import FakeS3, FakeSSM

ENV = {
    "MARKETPULSE_BUCKET": "bucket",
    "COINGECKO_API_KEY_PARAM": "/marketpulse/coingecko_api_key",
    "ALPHAVANTAGE_API_KEY_PARAM": "/marketpulse/alphavantage_api_key",
}
SSM = {"/marketpulse/coingecko_api_key": "cg-123", "/marketpulse/alphavantage_api_key": "av-456"}
DIA = date(2026, 10, 20)


# ---------- Ingesta ----------


@pytest.fixture
def fake_run_all(monkeypatch):
    """Sustituye run_all: escribe un fichero bronze y devuelve el resultado que le digamos."""
    state = {"results": {"frankfurter": None, "coingecko": None, "alphavantage": None}}

    def _run_all(watchlist, client, env, root):
        state["env"] = env
        write_bronze("frankfurter", [{"rate": 1.12}], dt=DIA, root=root)
        return state["results"]

    monkeypatch.setattr(ingest_handler, "run_all", _run_all)
    return state


def test_ingesta_pasa_las_claves_de_ssm_y_sube_bronze(fake_run_all, tmp_path):
    s3, ssm = FakeS3(), FakeSSM(SSM)
    summary = ingest_handler.run_ingest_job(s3, ssm, ENV, http=None, root=tmp_path)

    assert fake_run_all["env"]["COINGECKO_API_KEY"] == "cg-123"
    assert fake_run_all["env"]["ALPHAVANTAGE_API_KEY"] == "av-456"
    assert list(s3.objects) == ["bronze/source=frankfurter/dt=2026-10-20/frankfurter.json"]
    assert summary["uploaded"] == 1 and summary["failed"] == {}


def test_ingesta_no_cambia_el_entorno_original(fake_run_all, tmp_path):
    env = dict(ENV)
    ingest_handler.run_ingest_job(FakeS3(), FakeSSM(SSM), env, http=None, root=tmp_path)
    assert "COINGECKO_API_KEY" not in env  # las claves no se escriben en el entorno


def test_ingesta_con_una_fuente_mal_sube_lo_bueno_y_lanza_error(fake_run_all, tmp_path):
    fake_run_all["results"] = {"frankfurter": None, "coingecko": "HttpError: 429"}
    s3 = FakeS3()
    with pytest.raises(JobFailedError, match="coingecko"):
        ingest_handler.run_ingest_job(s3, FakeSSM(SSM), ENV, http=None, root=tmp_path)
    assert len(s3.objects) == 1  # lo que sí llegó está en S3 antes del error


@pytest.mark.parametrize("falta", ["MARKETPULSE_BUCKET", "ALPHAVANTAGE_API_KEY_PARAM"])
def test_ingesta_sin_configuracion_falla_antes_de_hacer_nada(fake_run_all, tmp_path, falta):
    env = {k: v for k, v in ENV.items() if k != falta}
    s3 = FakeS3()
    with pytest.raises(JobFailedError, match=falta):
        ingest_handler.run_ingest_job(s3, FakeSSM(SSM), env, http=None, root=tmp_path)
    assert "env" not in fake_run_all and s3.objects == {}


# ---------- Transformación ----------


@pytest.fixture
def s3_con_bronze():
    s3 = FakeS3()
    s3.objects["bronze/source=frankfurter/dt=2026-10-20/frankfurter.json"] = b"[]"
    return s3


def test_transformacion_descarga_bronze_y_sube_silver_y_gold(monkeypatch, s3_con_bronze, tmp_path):
    def fake_run_transform(watchlist, root):
        assert (root / "bronze" / "source=frankfurter").exists()  # bronze ya está en /tmp
        for layer in ("silver", "gold"):
            (root / layer / "t" / "year=2026").mkdir(parents=True)
            (root / layer / "t" / "year=2026" / "part-0.parquet").write_bytes(layer.encode())
        return True

    monkeypatch.setattr(transform_handler, "run_transform", fake_run_transform)
    summary = transform_handler.run_transform_job(s3_con_bronze, ENV, root=tmp_path)
    assert summary == {"bronze_downloaded": 1, "uploaded": 2, "unchanged": 0}
    assert "gold/t/year=2026/part-0.parquet" in s3_con_bronze.objects


def test_transformacion_con_calidad_mal_lanza_error_y_no_sube_nada(
    monkeypatch, s3_con_bronze, tmp_path
):
    monkeypatch.setattr(transform_handler, "run_transform", lambda watchlist, root: False)
    with pytest.raises(JobFailedError, match="calidad"):
        transform_handler.run_transform_job(s3_con_bronze, ENV, root=tmp_path)
    assert all(k.startswith("bronze/") for k in s3_con_bronze.objects)  # no se subió nada


def test_transformacion_sin_bronze_lanza_error(tmp_path):
    with pytest.raises(JobFailedError, match="bronze"):
        transform_handler.run_transform_job(FakeS3(), ENV, root=tmp_path)
