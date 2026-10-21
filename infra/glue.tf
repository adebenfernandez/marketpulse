# Glue Data Catalog: la "ficha" de cada tabla (columnas, tipos, formato y dónde están los ficheros).
# Los datos NO se mueven: siguen en S3. Athena lee la ficha y después los Parquet (schema-on-read).
# Sin crawlers (prohibidos en CLAUDE.md): el esquema lo escribimos nosotros, igual que en
# transform/schemas.py, y así un cambio de esquema siempre es un cambio revisado en el código.

resource "aws_glue_catalog_database" "marketpulse" {
  name        = var.project
  description = "Data lake de MarketPulse: tablas externas sobre la capa gold de S3"
}

resource "aws_glue_catalog_table" "daily_prices" {
  database_name = aws_glue_catalog_database.marketpulse.name
  name          = "daily_prices"
  description   = "Gold: un precio por dia y activo (cripto, bolsa y divisas) en formato largo"
  table_type    = "EXTERNAL_TABLE" # borrar la tabla no borra los ficheros de S3

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"

    # Partition projection: Athena CALCULA las particiones (year=2025, year=2026...) a partir de
    # estas reglas, en lugar de buscarlas en el catálogo. Sin crawlers ni MSCK REPAIR TABLE: una
    # partición nueva (year=2027) se puede consultar en cuanto la escribe la Lambda
    "projection.enabled"    = "true"
    "projection.year.type"  = "integer"
    "projection.year.range" = "2025,2040" # del primer dato del backfill hasta un margen amplio
  }

  # Columnas de partición: no están DENTRO de los Parquet, se leen de la ruta (year=2026/)
  partition_keys {
    name = "year"
    type = "int"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.datalake.bucket}/gold/daily_prices/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    # Mismo contrato que DAILY_PRICES en transform/schemas.py (date32 -> date, float64 -> double)
    columns {
      name    = "date"
      type    = "date"
      comment = "Fecha del dato. Palabra reservada en SQL: escribir \"date\" entre comillas dobles"
    }
    columns {
      name    = "asset"
      type    = "string"
      comment = "BTC, ETH, SOL, SPY, VT, QQQ, EUR/USD, EUR/GBP"
    }
    columns {
      name    = "asset_class"
      type    = "string"
      comment = "crypto | equity | fx"
    }
    columns {
      name    = "price"
      type    = "double"
      comment = "Precio del dia, en la moneda de currency"
    }
    columns {
      name    = "currency"
      type    = "string"
      comment = "Moneda de price (USD, GBP)"
    }
    columns {
      name    = "price_type"
      type    = "string"
      comment = "close (bolsa) | snapshot (cripto: foto diaria) | reference_rate (BCE)"
    }
    columns {
      name    = "source"
      type    = "string"
      comment = "alphavantage | coingecko | frankfurter"
    }
  }
}

# Dimensión de activos: 8 filas escritas por la Lambda de transformación desde watchlist.yaml.
# Sin particiones (un único Parquet): partir 8 filas en carpetas no ahorraría nada
resource "aws_glue_catalog_table" "dim_asset" {
  database_name = aws_glue_catalog_database.marketpulse.name
  name          = "dim_asset"
  description   = "Dimension de activos: una fila por activo de la watchlist con sus atributos"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.datalake.bucket}/gold/dim_asset/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    # Mismo contrato que DIM_ASSET en transform/schemas.py
    columns {
      name    = "asset"
      type    = "string"
      comment = "Clave del activo: la misma que en daily_prices y fact_daily_price"
    }
    columns {
      name    = "asset_name"
      type    = "string"
      comment = "Nombre legible (Bitcoin, SPDR S&P 500 ETF, Tipo de referencia BCE EUR/USD)"
    }
    columns {
      name    = "asset_class"
      type    = "string"
      comment = "crypto | equity | fx"
    }
    columns {
      name    = "currency"
      type    = "string"
      comment = "Moneda en la que se expresa el precio del activo"
    }
    columns {
      name    = "price_type"
      type    = "string"
      comment = "close (bolsa) | snapshot (cripto) | reference_rate (BCE)"
    }
    columns {
      name    = "source"
      type    = "string"
      comment = "alphavantage | coingecko | frankfurter"
    }
    columns {
      name    = "annualization_days"
      type    = "int"
      comment = "Sesiones al año para anualizar la volatilidad: 365 cripto, 252 bolsa y divisas"
    }
  }
}
