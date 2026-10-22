# Athena: dónde guarda los resultados y con qué límites se ejecutan las consultas.
#
# Cada consulta de Athena escribe su resultado (un CSV) y sus metadatos en S3, en el bucket del data
# lake bajo var.athena_results_prefix. La regla que los borra a los 7 días es del bucket, así que
# vive en el módulo storage (S3 admite UNA sola configuración de ciclo de vida por bucket).

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
      output_location = "s3://${var.bucket_name}/${var.athena_results_prefix}"

      encryption_configuration {
        encryption_option = "SSE_S3" # resultados cifrados, igual que el resto del bucket
      }
    }
  }
}
