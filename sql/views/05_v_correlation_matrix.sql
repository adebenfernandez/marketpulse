-- Matriz de correlaciones de los últimos 90 días: ¿se mueven juntos dos activos?
-- +1 = siempre en la misma dirección · 0 = sin relación · -1 = siempre en direcciones opuestas.
--
-- El punto delicado es ALINEAR FECHAS. Cripto cotiza todos los días y la bolsa no: el lunes, la
-- rentabilidad de v_daily_returns de SPY cubre viernes -> lunes, pero la de BTC solo domingo ->
-- lunes. Correlacionarlas tal cual mezclaría periodos distintos. Por eso, para CADA PAREJA:
--   1. Se cruzan los precios de los dos activos SOLO en las fechas en que existen los dos (JOIN
--      por fecha): con SPY, el fin de semana de BTC desaparece.
--   2. Se calculan las rentabilidades sobre esas fechas comunes (LAG dentro de la pareja), así que
--      las dos cubren SIEMPRE el mismo periodo (viernes -> lunes para las dos).
--   3. corr() (correlación de Pearson) sobre esas parejas de rentabilidades.
-- Salen las 64 combinaciones (8 x 8): la diagonal vale 1 y la matriz es simétrica (A-B = B-A).
-- Ventana fija de 90 días naturales para que todas las parejas comparen el mismo periodo reciente.
CREATE OR REPLACE VIEW v_correlation_matrix AS
WITH recent AS (
    SELECT "date", asset, price
    FROM fact_daily_price
    WHERE "date" >= date_add('day', -90, current_date)
),
pairs AS (
    SELECT
        a.asset AS asset_a,
        b.asset AS asset_b,
        a."date",
        a.price AS price_a,
        b.price AS price_b
    FROM recent AS a
    JOIN recent AS b ON a."date" = b."date"  -- solo las fechas que comparten los dos activos
),
pair_returns AS (
    SELECT
        asset_a,
        asset_b,
        "date",
        ln(price_a / LAG(price_a) OVER (PARTITION BY asset_a, asset_b ORDER BY "date")) AS return_a,
        ln(price_b / LAG(price_b) OVER (PARTITION BY asset_a, asset_b ORDER BY "date")) AS return_b
    FROM pairs
)
SELECT
    asset_a,
    asset_b,
    count(*) AS n_obs,
    min("date") AS first_date,
    max("date") AS last_date,
    corr(return_a, return_b) AS correlation
FROM pair_returns
WHERE return_a IS NOT NULL AND return_b IS NOT NULL
GROUP BY asset_a, asset_b
