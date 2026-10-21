-- Tabla de hechos del modelo en estrella. Granularidad: UNA fila por (día, activo).
-- Solo claves y medidas: lo descriptivo del activo (clase, moneda, tipo de precio, fuente) está en
-- dim_asset, y lo del calendario en dim_date. Se cruzan por "asset" y por "date".
-- Se queda `year` (la partición) para poder filtrar por año y leer menos bytes.
CREATE OR REPLACE VIEW fact_daily_price AS
SELECT
    "date",
    asset,
    price,
    year
FROM daily_prices
