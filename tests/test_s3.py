"""Tests de la subida a S3 con un S3 FALSO en memoria: sin AWS, sin credenciales, sin coste."""

import hashlib
import logging
from datetime import date

import pytest

from marketpulse.common import s3
from marketpulse.common.storage import write_bronze


class FakeS3:
    """Imita lo que usamos del cliente de boto3: put_object y el paginador de list_objects_v2."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.puts = 0

    def put_object(self, Bucket, Key, Body, ContentType):  # noqa: N803 (nombres de boto3)
        self.objects[Key] = Body
        self.puts += 1

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return self

    def paginate(self, Bucket, Prefix):  # noqa: N803
        contents = [
            {"Key": k, "ETag": f'"{hashlib.md5(v).hexdigest()}"'}  # con comillas, como el real
            for k, v in sorted(self.objects.items())
            if k.startswith(Prefix)
        ]
        yield {"Contents": contents} if contents else {}


@pytest.fixture
def lake(tmp_path):
    write_bronze("frankfurter", [{"rate": 1.12}], dt=date(2026, 10, 20), root=tmp_path)
    write_bronze("alphavantage", {"x": 1}, dt=date(2026, 10, 20), name="SPY", root=tmp_path)
    gold = tmp_path / "gold" / "daily_prices" / "year=2026"
    gold.mkdir(parents=True)
    (gold / "part-0.parquet").write_bytes(b"PAR1 datos de prueba")
    return tmp_path


def test_sube_todo_con_las_mismas_rutas_y_barras_de_s3(lake):
    fake = FakeS3()
    result = s3.upload_layers(fake, "bucket", root=lake)
    assert result == {"uploaded": 3, "unchanged": 0}
    assert sorted(fake.objects) == [
        "bronze/source=alphavantage/dt=2026-10-20/SPY.json",
        "bronze/source=frankfurter/dt=2026-10-20/frankfurter.json",
        "gold/daily_prices/year=2026/part-0.parquet",
    ]  # con '/' aunque en Windows la ruta local use '\'


def test_segunda_subida_sin_cambios_no_hace_ningun_put(lake):
    fake = FakeS3()
    s3.upload_layers(fake, "bucket", root=lake)
    result = s3.upload_layers(fake, "bucket", root=lake)
    assert result == {"uploaded": 0, "unchanged": 3}
    assert fake.puts == 3  # solo los de la primera vez


def test_un_fichero_cambiado_se_vuelve_a_subir_y_sobrescribe(lake):
    fake = FakeS3()
    s3.upload_layers(fake, "bucket", root=lake)
    write_bronze("frankfurter", [{"rate": 1.13}], dt=date(2026, 10, 20), root=lake)  # cambia
    result = s3.upload_layers(fake, "bucket", root=lake)
    assert result == {"uploaded": 1, "unchanged": 2}
    assert len(fake.objects) == 3  # sobrescrito, no duplicado
    assert b"1.13" in fake.objects["bronze/source=frankfurter/dt=2026-10-20/frankfurter.json"]


def test_ignora_temporales_y_capas_que_no_existen(lake):
    (lake / "gold" / ".daily_prices.tmp").mkdir()
    (lake / "gold" / ".daily_prices.tmp" / "part-0.parquet").write_bytes(b"a medias")
    fake = FakeS3()
    s3.upload_layers(fake, "bucket", root=lake)  # no hay silver/: no debe fallar
    assert not any(".tmp" in k for k in fake.objects)


def test_main_sin_bucket_da_error_sin_llamar_a_aws(monkeypatch, caplog):
    monkeypatch.setattr("dotenv.load_dotenv", lambda: None)  # no leer tu .env real
    monkeypatch.setenv(s3.BUCKET_ENV, "  ")
    with caplog.at_level(logging.ERROR):
        assert s3.main() == 1
    assert "MARKETPULSE_BUCKET" in caplog.text
