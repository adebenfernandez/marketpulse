"""Tests del validador de SQL del agente (paso 7.2, D-030).

Cada ataque es un caso de `parametrize`: si alguien relaja una regla, el test dice cuál.
"""

import re
from pathlib import Path

import pytest

from marketpulse.agent.guard import (
    ALLOWED_TABLES,
    MAX_LIMIT,
    SqlRejectedError,
    validate_sql,
)

ROOT = Path(__file__).resolve().parents[1]


# --- Lo que SÍ debe pasar ---------------------------------------------------------------------


def test_select_sencillo_pasa_y_conserva_su_limit():
    v = validate_sql("SELECT asset, price FROM daily_prices WHERE year = 2026 LIMIT 5")
    assert v.tables == ("daily_prices",)
    assert v.limit == 5
    assert v.limit_changed is False
    assert v.sql.endswith("LIMIT 5")


def test_sin_limit_se_anade_el_maximo():
    v = validate_sql("SELECT asset FROM dim_asset")
    assert v.limit == MAX_LIMIT
    assert v.limit_changed is True
    assert v.sql.endswith(f"LIMIT {MAX_LIMIT}")


def test_limit_demasiado_grande_se_recorta():
    v = validate_sql("SELECT * FROM v_daily_returns LIMIT 50000")
    assert v.limit == MAX_LIMIT
    assert v.limit_changed is True
    assert "50000" not in v.sql


def test_cte_union_y_subconsulta_pasan():
    sql = """
        WITH ultimos AS (
            SELECT asset, max("date") AS d FROM fact_daily_price GROUP BY asset
        )
        SELECT u.asset, f.price
        FROM ultimos u JOIN (SELECT * FROM fact_daily_price) f
          ON f.asset = u.asset AND f."date" = u.d
        UNION ALL
        SELECT asset, NULL FROM dim_asset
    """
    v = validate_sql(sql)
    assert v.tables == ("dim_asset", "fact_daily_price")  # la CTE "ultimos" no cuenta
    assert v.limit_changed is True


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM marketpulse.dim_asset",
        "SELECT * FROM awsdatacatalog.marketpulse.dim_asset",
        'SELECT * FROM "DIM_ASSET"',  # Athena no distingue mayúsculas
        "SELECT * FROM dim_asset;",  # un ";" final no es una segunda sentencia
        "SELECT 1 -- ; DROP TABLE daily_prices",  # el DROP está dentro de un comentario
        "SELECT 'DROP TABLE daily_prices' AS texto",  # ... o dentro de una cadena
    ],
)
def test_formas_validas_de_leer(sql):
    validate_sql(sql)


def test_la_lista_blanca_coincide_con_las_tablas_y_las_vistas_desplegadas():
    views = {re.sub(r"^\d+_", "", p.stem) for p in (ROOT / "sql" / "views").glob("*.sql")}
    glue_tf = (ROOT / "infra" / "modules" / "analytics" / "glue.tf").read_text(encoding="utf-8")
    tables = set(re.findall(r'^\s*name\s*=\s*"(\w+)"', glue_tf, flags=re.MULTILINE))
    tables -= {"year", "date", "asset", "asset_class", "price", "currency", "price_type"}
    tables -= {"source", "asset_name", "annualization_days"}  # columnas, no tablas
    assert ALLOWED_TABLES == views | tables


# --- Lo que NO debe pasar ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sql", "code"),
    [
        ("", "vacia"),
        ("   \n ", "vacia"),
        ("SELECT 1 " + " " * 10_000, "demasiado_larga"),
        ("SELEC asset FROM", "no_se_puede_analizar"),
        ("DROP TABLE daily_prices", "no_es_select"),
        ("SELECT 1; DROP TABLE daily_prices", "varias_sentencias"),
        ("SELECT 1; SELECT 2", "varias_sentencias"),
        ("DELETE FROM daily_prices", "no_es_select"),
        ("INSERT INTO daily_prices SELECT * FROM daily_prices", "no_es_select"),
        ("CREATE TABLE copia AS SELECT * FROM daily_prices", "no_es_select"),
        ("CREATE OR REPLACE VIEW v_daily_returns AS SELECT 1", "no_es_select"),
        ("ALTER TABLE daily_prices ADD COLUMNS (x int)", "no_es_select"),
        ("UNLOAD (SELECT * FROM daily_prices) TO 's3://otro-bucket/'", "no_es_select"),
        ("SHOW TABLES", "no_es_select"),
        ("DESCRIBE daily_prices", "no_es_select"),
        ("MSCK REPAIR TABLE daily_prices", "no_es_select"),
        ("SELECT * INTO nueva FROM daily_prices", "operacion_prohibida"),
        ("SELECT * FROM otra_base.daily_prices", "tabla_no_permitida"),
        ("SELECT * FROM otrocatalogo.marketpulse.daily_prices", "tabla_no_permitida"),
        ("SELECT * FROM information_schema.tables", "tabla_no_permitida"),
        ("SELECT * FROM tabla_inventada", "tabla_no_permitida"),
        ("SELECT * FROM daily_prices FETCH FIRST 3 ROWS ONLY", "limit_no_valido"),
        ("SELECT * FROM daily_prices LIMIT 10 + 1", "limit_no_valido"),
    ],
)
def test_se_rechaza(sql, code):
    with pytest.raises(SqlRejectedError) as info:
        validate_sql(sql)
    assert info.value.code == code


def test_una_cte_no_puede_tapar_una_tabla_de_otra_base():
    # "x" es una CTE, pero otra_base.x es una tabla de verdad de otra base: se rechaza
    sql = "WITH x AS (SELECT 1 AS n) SELECT * FROM otra_base.x"
    with pytest.raises(SqlRejectedError) as info:
        validate_sql(sql)
    assert info.value.code == "tabla_no_permitida"


def test_el_mensaje_dice_el_motivo():
    with pytest.raises(SqlRejectedError) as info:
        validate_sql("SELECT * FROM tabla_inventada")
    assert "tabla_inventada" in str(info.value)
