-- Dimensión de fechas: una fila por día del calendario desde 2025-01-01 hasta hoy.
-- No se guarda en S3: se GENERA al consultarla (sequence + UNNEST), así que nunca se queda corta.
-- Sirve para preguntas de calendario ("solo lunes", "por trimestre", "fines de semana") sin
-- repetir funciones de fecha en cada consulta.
-- En Athena, sequence() solo acepta timestamps con INTERVAL (no fechas), y una vista no puede
-- exponer columnas timestamp(0): por eso la subconsulta convierte cada día a `date` ANTES de
-- calcular nada (dos errores reales del paso 4.5).
CREATE OR REPLACE VIEW dim_date AS
SELECT
    d AS "date",
    year(d) AS year,
    quarter(d) AS quarter,
    month(d) AS month,
    day(d) AS day_of_month,
    day_of_week(d) AS day_of_week,  -- ISO: 1 = lunes ... 7 = domingo
    day_of_week(d) IN (6, 7) AS is_weekend,
    week_of_year(d) AS iso_week,
    CAST(date_trunc('month', d) AS date) AS month_start,
    substr(CAST(d AS varchar), 1, 7) AS year_month  -- '2026-10'
FROM (
    SELECT CAST(ts AS date) AS d
    FROM UNNEST(
        sequence(TIMESTAMP '2025-01-01 00:00:00', CAST(current_date AS timestamp), INTERVAL '1' DAY)
    ) AS t (ts)
)
