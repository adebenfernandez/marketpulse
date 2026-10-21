-- Rentabilidad diaria de cada activo: cuánto ha cambiado su precio respecto a su sesión ANTERIOR.
--
-- La función ventana LAG(price) OVER (PARTITION BY asset ORDER BY "date") mira "una fila atrás"
-- dentro de la serie de CADA activo (PARTITION BY: no mezcla BTC con SPY), en orden de fecha.
-- Por eso el lunes de una acción se compara con el viernes (no hay filas de fin de semana) y en
-- cripto cada día con el anterior: es la "sesión anterior del mismo activo" (nota del paso 2.4),
-- nunca "ayer" en el calendario. days_since_prev lo deja a la vista (1, 3 tras un fin de semana...).
--
-- Dos formas de medir el cambio:
--   simple_return = precio / precio_anterior - 1        (+0.02 = sube un 2 %)
--   log_return    = ln(precio / precio_anterior)        (casi igual para cambios pequeños, pero
--                   se SUMA a lo largo del tiempo: la de una semana = suma de las de cada día. Es
--                   la que se usa para volatilidades y correlaciones, pasos 4.7 y 4.8)
-- La primera fila de cada activo no tiene anterior: se descarta (no hay rentabilidad).
CREATE OR REPLACE VIEW v_daily_returns AS
WITH with_previous AS (
    SELECT
        f."date",
        f.asset,
        a.asset_class,
        f.price,
        LAG(f.price) OVER (PARTITION BY f.asset ORDER BY f."date") AS prev_price,
        LAG(f."date") OVER (PARTITION BY f.asset ORDER BY f."date") AS prev_date,
        f.year
    FROM fact_daily_price AS f
    JOIN dim_asset AS a ON f.asset = a.asset
)
SELECT
    "date",
    asset,
    asset_class,
    price,
    prev_date,
    prev_price,
    date_diff('day', prev_date, "date") AS days_since_prev,
    price / prev_price - 1 AS simple_return,
    ln(price / prev_price) AS log_return,
    year
FROM with_previous
WHERE prev_price IS NOT NULL
