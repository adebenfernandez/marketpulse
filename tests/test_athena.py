"""Tests del cliente de Athena con un Athena FALSO: sin AWS, sin coste."""

import pytest

from marketpulse.common.athena import (
    AthenaQueryError,
    deploy_views,
    format_table,
    run_query,
    sql_from_file,
)


class FakeAthena:
    """Imita start/get/stop_query_execution y el paginador de get_query_results."""

    def __init__(self, states, rows=(), statement_type="DML", reason=None):
        self.states = list(states)  # estados que irá devolviendo get_query_execution
        self.rows = [list(r) for r in rows]
        self.statement_type = statement_type
        self.reason = reason
        self.started = []
        self.stopped = []

    def start_query_execution(self, **kwargs):
        self.started.append(kwargs)
        return {"QueryExecutionId": "q-1"}

    def get_query_execution(self, QueryExecutionId):  # noqa: N803 (nombres de boto3)
        state = self.states.pop(0) if len(self.states) > 1 else self.states[0]
        status = {"State": state}
        if self.reason:
            status["StateChangeReason"] = self.reason
        return {
            "QueryExecution": {
                "Status": status,
                "StatementType": self.statement_type,
                "Statistics": {"DataScannedInBytes": 1234, "TotalExecutionTimeInMillis": 456},
            }
        }

    def stop_query_execution(self, QueryExecutionId):  # noqa: N803
        self.stopped.append(QueryExecutionId)

    def get_paginator(self, name):
        assert name == "get_query_results"
        return self

    def paginate(self, QueryExecutionId):  # noqa: N803
        header = self.rows[0] if self.rows else []
        yield {
            "ResultSet": {
                "ResultSetMetadata": {"ColumnInfo": [{"Name": n} for n in header]},
                "Rows": [{"Data": [{"VarCharValue": v} for v in r]} for r in self.rows],
            }
        }


def test_espera_a_que_termine_y_quita_la_fila_de_cabecera():
    fake = FakeAthena(["QUEUED", "RUNNING", "SUCCEEDED"], rows=[["clase", "n"], ["fx", "510"]])
    esperas = []
    result = run_query(fake, "SELECT ...", sleep=esperas.append)
    assert result.columns == ["clase", "n"]
    assert result.rows == [["fx", "510"]]  # la cabecera no cuenta como fila
    assert (result.bytes_scanned, result.elapsed_ms) == (1234, 456)
    assert len(esperas) == 2  # preguntó 3 veces: QUEUED, RUNNING y SUCCEEDED


def test_usa_el_workgroup_y_la_base_de_datos_del_proyecto():
    fake = FakeAthena(["SUCCEEDED"], rows=[["x"], ["1"]])
    run_query(fake, "SELECT 1 AS x", sleep=lambda s: None)
    assert fake.started == [
        {
            "QueryString": "SELECT 1 AS x",
            "WorkGroup": "marketpulse",
            "QueryExecutionContext": {"Database": "marketpulse"},
        }
    ]


def test_consulta_fallida_lanza_error_con_el_motivo():
    fake = FakeAthena(["FAILED"], reason="COLUMN_NOT_FOUND: price2")
    with pytest.raises(AthenaQueryError, match="COLUMN_NOT_FOUND"):
        run_query(fake, "SELECT price2 FROM daily_prices", sleep=lambda s: None)


def test_si_tarda_demasiado_la_para_y_lanza_error():
    fake = FakeAthena(["RUNNING"])
    with pytest.raises(AthenaQueryError, match="sin terminar"):
        run_query(fake, "SELECT ...", timeout_s=1, poll_s=0.5, sleep=lambda s: None)
    assert fake.stopped == ["q-1"]  # no la deja corriendo (y gastando)


def test_ddl_no_quita_ninguna_fila():
    fake = FakeAthena(["SUCCEEDED"], rows=[], statement_type="DDL")
    assert run_query(fake, "CREATE VIEW ...", sleep=lambda s: None).rows == []


def test_format_table_alinea_y_muestra_null():
    fake = FakeAthena(["SUCCEEDED"], rows=[["asset", "price"], ["BTC", None]])
    texto = format_table(run_query(fake, "SELECT ...", sleep=lambda s: None))
    assert texto.splitlines() == ["asset | price", "------+------", "BTC   | NULL "]


def test_sql_from_file_quita_cabecera_y_punto_y_coma(tmp_path):
    f = tmp_path / "v.sql"
    f.write_text("-- comentario\n-- otro\n\nCREATE OR REPLACE VIEW v AS\nSELECT 1 -- dentro\n;\n")
    assert sql_from_file(f) == "CREATE OR REPLACE VIEW v AS\nSELECT 1 -- dentro"


def test_deploy_views_en_orden_alfabetico(tmp_path):
    (tmp_path / "02_b.sql").write_text("CREATE OR REPLACE VIEW b AS SELECT * FROM a")
    (tmp_path / "01_a.sql").write_text("CREATE OR REPLACE VIEW a AS SELECT 1 AS x")
    fake = FakeAthena(["SUCCEEDED"], statement_type="DDL")
    assert deploy_views(fake, tmp_path, sleep=lambda s: None) == ["01_a.sql", "02_b.sql"]
    assert [s["QueryString"] for s in fake.started] == [
        "CREATE OR REPLACE VIEW a AS SELECT 1 AS x",
        "CREATE OR REPLACE VIEW b AS SELECT * FROM a",
    ]


def test_deploy_views_sin_ficheros_es_error(tmp_path):
    with pytest.raises(AthenaQueryError, match="No hay ficheros"):
        deploy_views(FakeAthena(["SUCCEEDED"]), tmp_path)
