-- Volatilidad móvil a 30 sesiones: cuánto "se mueve" cada activo, día a día, en el último mes y
-- medio de bolsa (o el último mes de cripto).
--
-- Volatilidad = desviación típica de las rentabilidades logarítmicas diarias. Se calcula con una
-- ventana MÓVIL: para cada día, STDDEV_SAMP sobre ESE día y los 29 anteriores del MISMO activo:
--     OVER (PARTITION BY asset ORDER BY "date" ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)
-- ROWS cuenta filas (sesiones), no días de calendario: 30 observaciones siempre, sea cripto (30
-- días) o bolsa (unas 6 semanas). Así las cifras son comparables estadísticamente.
--
-- Anualizar: la varianza crece con el tiempo, así que la desviación crece con su raíz cuadrada.
--     volatilidad anual = volatilidad diaria * sqrt(sesiones al año)
-- con 365 en cripto y 252 en bolsa y divisas (dim_asset.annualization_days). Es la cifra que se
-- suele publicar ("BTC tiene una volatilidad anual del 45 %").
--
-- Solo se publican los días con las 30 observaciones completas (n_obs = 30): con menos, la cifra
-- no es comparable con las demás.
CREATE OR REPLACE VIEW v_rolling_volatility_30d AS
WITH windowed AS (
    SELECT
        r."date",
        r.asset,
        r.asset_class,
        a.annualization_days,
        COUNT(r.log_return) OVER (
            PARTITION BY r.asset ORDER BY r."date" ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) AS n_obs,
        AVG(r.log_return) OVER (
            PARTITION BY r.asset ORDER BY r."date" ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) AS mean_log_return_30,
        STDDEV_SAMP(r.log_return) OVER (
            PARTITION BY r.asset ORDER BY r."date" ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) AS daily_volatility_30,
        r.year
    FROM v_daily_returns AS r
    JOIN dim_asset AS a ON r.asset = a.asset
)
SELECT
    "date",
    asset,
    asset_class,
    n_obs,
    mean_log_return_30,
    daily_volatility_30,
    daily_volatility_30 * sqrt(annualization_days) AS annualized_volatility_30,
    annualization_days,
    year
FROM windowed
WHERE n_obs = 30
