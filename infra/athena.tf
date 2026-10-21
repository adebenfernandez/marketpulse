# Athena: dónde guarda los resultados y con qué límites se ejecutan las consultas.
#
# Cada consulta de Athena escribe su resultado (un CSV) y sus metadatos en S3. Los guardamos en el
# mismo bucket, bajo el prefijo athena-results/, y una regla de ciclo de vida los borra a los
# 7 días (regla de costes de CLAUDE.md): son copias que se pueden regenerar volviendo a consultar.

locals {
  athena_results_prefix = "athena-results/"
}

resource "aws_s3_bucket_lifecycle_configuration" "datalake" {
  bucket = aws_s3_bucket.datalake.id

  # OJO: esta configuración es la ÚNICA del bucket (S3 admite una sola). Si más adelante hace falta
  # otra regla (p. ej. para bronze), se añade aquí como otro bloque "rule"
  rule {
    id     = "borrar-resultados-athena"
    status = "Enabled"

    filter {
      prefix = local.athena_results_prefix # solo los resultados: bronze, silver y gold NO se tocan
    }

    expiration {
      days = 7
    }

    # Las consultas fallidas o canceladas pueden dejar subidas "multiparte" a medias, que ocupan
    # espacio (y se cobran) sin verse como objetos. AWS recomienda abortarlas con esta regla
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

resource "aws_athena_workgroup" "marketpulse" {
  name        = var.project
  description = "Consultas de MarketPulse: resultados en S3 con borrado a los 7 dias y limite de 100 MB"
  state       = "ENABLED"

  configuration {
    # Obliga a usar ESTA configuración aunque el cliente (consola, boto3) pida otra ubicación o
    # quiera saltarse el límite: el workgroup manda
    enforce_workgroup_configuration = true

    # Límite por consulta: si una consulta va a leer más de 100 MB, Athena la CANCELA.
    # Nuestros datos ocupan KB: una consulta que pase de 100 MB solo puede ser un error
    bytes_scanned_cutoff_per_query = 100 * 1024 * 1024

    # Sin métricas en CloudWatch: los bytes escaneados ya vienen en cada ejecución
    # (get-query-execution -> DataScannedInBytes), y así no añadimos un coste sin comprobar
    publish_cloudwatch_metrics_enabled = false

    engine_version {
      selected_engine_version = "Athena engine version 3" # basado en Trino
    }

    result_configuration {
      output_location = "s3://${aws_s3_bucket.datalake.bucket}/${local.athena_results_prefix}"

      encryption_configuration {
        encryption_option = "SSE_S3" # resultados cifrados, igual que el resto del bucket
      }
    }
  }
}
