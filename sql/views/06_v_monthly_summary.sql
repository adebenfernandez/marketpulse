-- Resumen mensual por activo: precio de apertura y de cierre del mes, rango, rentabilidad del mes,
-- volatilidad y mejor y peor día. Es la vista para preguntas tipo "¿qué tal fue BTC en septiembre?".
--
-- Funciones ventana:
--   first_value(price) / last_value(price) OVER (PARTITION BY asset, month ORDER BY "date" ...)
--   dan el primer y el último precio de cada activo en cada mes.
--   TRAMPA CLÁSICA: con ORDER BY, el marco por defecto es "desde el principio hasta la fila
--   ACTUAL", así que last_value devolvería el precio de la propia fila, no el del último día. Hay
--   que ampliar el marco a todo el grupo:
--   ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING.
--
-- Rentabilidad del mes = exp(suma de las rentabilidades logarítmicas diarias) - 1.
-- Como las logarítmicas se SUMAN, esto es exactamente cierre del mes / cierre del mes anterior - 1
-- (incluye el salto del último día del mes anterior al primero de este, que first/last no ven).
-- month_to_date = true marca el mes en curso (aún incompleto). El primer mes de cada activo
-- también es parcial: empieza donde empieza su historia.
CREATE OR REPLACE VIEW v_monthly_summary AS
WITH daily AS (
    SELECT
        f.asset,
        a.asset_class,
        a.currency,
        date_trunc('month', f."date") AS month,
        f."date",
        f.price,
        r.log_return,  -- NULL el primer día de la historia de cada activo
        first_value(f.price) OVER (
            PARTITION BY f.asset, date_trunc('month', f."date") ORDER BY f."date"
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS open_price,
        last_value(f.price) OVER (
            PARTITION BY f.asset, date_trunc('month', f."date") ORDER BY f."date"
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS close_price
    FROM fact_daily_price AS f
    JOIN dim_asset AS a ON f.asset = a.asset
    LEFT JOIN v_daily_returns AS r ON r.asset = f.asset AND r."date" = f."date"
)
SELECT
    asset,
    asset_class,
    currency,
    month,
    count(*) AS sessions,
    min("date") AS first_date,
    max("date") AS last_date,
    max(open_price) AS open_price,  -- es igual en todas las filas del grupo: max() solo lo recoge
    max(close_price) AS close_price,
    min(price) AS min_price,
    max(price) AS max_price,
    exp(sum(log_return)) - 1 AS monthly_return,
    stddev_samp(log_return) AS daily_volatility,
    min(log_return) AS worst_day_log_return,
    max(log_return) AS best_day_log_return,
    month = date_trunc('month', current_date) AS month_to_date
FROM daily
GROUP BY asset, asset_class, currency, month
