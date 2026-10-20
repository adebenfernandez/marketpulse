"""Dobles de prueba (fakes) de los clientes de boto3: imitan solo lo que usa MarketPulse.

Viven aquí porque los usan varios ficheros de tests (S3, SSM y los handlers de Lambda).
"""

import hashlib
import io


class FakeS3:
    """S3 en memoria: put_object, get_object y el paginador de list_objects_v2."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.puts = 0

    def put_object(self, Bucket, Key, Body, ContentType):  # noqa: N803 (nombres de boto3)
        self.objects[Key] = Body
        self.puts += 1

    def get_object(self, Bucket, Key):  # noqa: N803
        # boto3 devuelve el contenido como un "stream" que se lee con .read()
        return {"Body": io.BytesIO(self.objects[Key])}

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


class FakeSSM:
    """Parameter Store en memoria. Apunta cada llamada para comprobar CÓMO se pidió."""

    def __init__(self, params: dict[str, str]):
        self.params = params
        self.calls: list[dict] = []

    def get_parameters(self, Names, WithDecryption):  # noqa: N803
        self.calls.append({"Names": Names, "WithDecryption": WithDecryption})
        return {
            "Parameters": [{"Name": n, "Value": self.params[n]} for n in Names if n in self.params],
            "InvalidParameters": [n for n in Names if n not in self.params],
        }
