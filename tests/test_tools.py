"""Tests de las herramientas del agente (paso 7.6, D-034), con Glue y Athena FALSOS."""

import json

import pytest
from botocore.exceptions import ClientError

from marketpulse.agent.guard import ALLOWED_TABLES
from marketpulse.agent.tools import (
    MAX_ROWS,
    TABLE_DESCRIPTIONS,
    TOOL_DEFINITIONS,
    AgentTools,
)
from tests.test_athena import FakeAthena


class FakeGlue:
    """Imita glue.get_table y cuenta las llamadas (para comprobar la caché)."""

    def __init__(self):
        self.calls = []

    def get_table(self, DatabaseName, Name):  # noqa: N803 (nombres de boto3)
        self.calls.append((DatabaseName, Name))
        if Name == "daily_prices":
            return {
                "Table": {
                    "TableType": "EXTERNAL_TABLE",
                    "StorageDescriptor": {
                        "Columns": [
                            {"Name": "date", "Type": "date", "Comment": "Fecha del dato"},
                            {"Name": "price", "Type": "double"},
                        ]
                    },
                    "PartitionKeys": [{"Name": "year", "Type": "int", "Comment": "Año"}],
                }
            }
        return {
            "Table": {
                "TableType": "VIRTUAL_VIEW",
                "StorageDescriptor": {"Columns": [{"Name": "asset", "Type": "string"}]},
            }
        }


def tools_with(athena=None):
    return AgentTools(FakeGlue(), athena or FakeAthena(["SUCCEEDED"]))


def payload(result):
    return json.loads(result.content)


# --- Definiciones que se envían a la API ---


def test_hay_tres_herramientas_con_esquema_estricto():
    assert [t["name"] for t in TOOL_DEFINITIONS] == ["list_tables", "describe_table", "run_query"]
    for tool in TOOL_DEFINITIONS:
        assert tool["strict"] is True
        assert tool["input_schema"]["additionalProperties"] is False
        assert set(tool["input_schema"].get("required", [])) == set(
            tool["input_schema"]["properties"]
        )


def test_todas_las_tablas_permitidas_tienen_descripcion():
    assert set(TABLE_DESCRIPTIONS) == ALLOWED_TABLES


# --- list_tables y describe_table ---


def test_list_tables_devuelve_la_lista_blanca_sin_llamar_a_glue():
    tools = tools_with()
    data = payload(tools.execute("list_tables", {}))
    assert {t["name"] for t in data["tables"]} == ALLOWED_TABLES
    assert tools.glue.calls == []


def test_describe_table_junta_columnas_y_particiones():
    data = payload(tools_with().execute("describe_table", {"table_name": "daily_prices"}))
    assert data["kind"] == "table"
    assert [c["name"] for c in data["columns"]] == ["date", "price", "year"]
    assert data["partition_columns"] == ["year"]
    assert data["columns"][0]["comment"] == "Fecha del dato"


def test_describe_table_de_una_vista_y_en_mayusculas():
    data = payload(tools_with().execute("describe_table", {"table_name": " V_Daily_Returns "}))
    assert (data["name"], data["kind"]) == ("v_daily_returns", "view")


def test_describe_table_usa_cache():
    tools = tools_with()
    tools.execute("describe_table", {"table_name": "dim_asset"})
    tools.execute("describe_table", {"table_name": "dim_asset"})
    assert tools.glue.calls == [("marketpulse", "dim_asset")]


@pytest.mark.parametrize("name", ["information_schema.tables", "otra_tabla", "", "../silver"])
def test_describe_table_fuera_de_la_lista_es_error_y_no_pregunta_a_glue(name):
    tools = tools_with()
    result = tools.execute("describe_table", {"table_name": name})
    assert result.is_error
    assert tools.glue.calls == []


# --- run_query ---


def test_run_query_valida_ejecuta_y_registra_el_intento():
    athena = FakeAthena(["SUCCEEDED"], rows=[["asset", "price"], ["BTC", "82850.0"]])
    tools = tools_with(athena)
    result = tools.execute("run_query", {"sql": "SELECT asset, price FROM daily_prices"})

    assert not result.is_error
    data = payload(result)
    assert data["rows"] == [["BTC", "82850.0"]]
    assert data["limit"] == MAX_ROWS
    # A Athena le llega la SQL VALIDADA (con el LIMIT añadido), no la del modelo
    assert athena.started[0]["QueryString"].endswith(f"LIMIT {MAX_ROWS}")
    [attempt] = tools.attempts
    assert attempt.sql_executed.endswith(f"LIMIT {MAX_ROWS}")
    assert (attempt.tables, attempt.rows, attempt.bytes_scanned) == (("daily_prices",), 1, 1234)
    assert attempt.block_code is None


def test_un_drop_table_no_llega_a_athena_y_queda_registrado():
    athena = FakeAthena(["SUCCEEDED"])
    tools = tools_with(athena)
    result = tools.execute("run_query", {"sql": "DROP TABLE daily_prices"})

    assert result.is_error
    assert "no_es_select" in payload(result)["error"]
    assert athena.started == []  # Athena ni se entera
    [attempt] = tools.attempts
    assert (attempt.block_code, attempt.sql_executed) == ("no_es_select", None)


def test_el_limit_del_agente_es_max_rows():
    athena = FakeAthena(["SUCCEEDED"])
    tools_with(athena).execute("run_query", {"sql": "SELECT * FROM dim_asset LIMIT 500"})
    assert athena.started[0]["QueryString"].endswith(f"LIMIT {MAX_ROWS}")


def test_error_de_athena_vuelve_al_modelo_sin_el_numero_de_cuenta():
    motivo = "User: arn:aws:sts::123456789012:assumed-role/marketpulse-agent/x is not authorized"
    athena = FakeAthena(["FAILED"], reason=motivo)
    tools = tools_with(athena)
    result = tools.execute("run_query", {"sql": "SELECT * FROM dim_asset"})

    assert result.is_error
    assert "123456789012" not in result.content
    assert "<cuenta>" in result.content
    assert "123456789012" in tools.attempts[0].error  # completo solo en el registro local


def test_athena_rechaza_la_consulta_al_lanzarla_y_el_error_vuelve_al_modelo():
    # Caso real de la evaluación (q12): comillas tipográficas → InvalidRequestException en start
    class AthenaQueRechaza(FakeAthena):
        def start_query_execution(self, **kwargs):
            raise ClientError(
                {"Error": {"Code": "InvalidRequestException", "Message": "line 1:8: mismatched"}},
                "StartQueryExecution",
            )

    tools = tools_with(AthenaQueRechaza(["SUCCEEDED"]))
    result = tools.execute("run_query", {"sql": "SELECT month(“date”) FROM daily_prices"})
    assert result.is_error
    assert "InvalidRequestException" in payload(result)["error"]
    assert "InvalidRequestException" in tools.attempts[0].error


def test_herramienta_desconocida_es_error():
    result = tools_with().execute("borrar_todo", {})
    assert result.is_error
    assert "desconocida" in payload(result)["error"]
