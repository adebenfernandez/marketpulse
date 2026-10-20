# Valores que Terraform muestra al terminar (y que se consultan con `terraform output`).
# El código de Python los necesitará para saber a qué bucket subir los datos.

output "datalake_bucket_name" {
  description = "Nombre del bucket del data lake"
  value       = aws_s3_bucket.datalake.bucket
}

output "datalake_bucket_arn" {
  description = "ARN del bucket (se usará en las políticas de IAM de la Fase 3)"
  value       = aws_s3_bucket.datalake.arn
}
