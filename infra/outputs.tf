# Valores que Terraform muestra al terminar (y que se consultan con `terraform output`).
# El código de Python los necesitará para saber a qué bucket subir los datos.

output "datalake_bucket_name" {
  description = "Nombre del bucket del data lake"
  value       = aws_s3_bucket.datalake.bucket
}

output "api_key_parameter_names" {
  description = "Nombres de los parámetros de SSM con las claves de API (el valor NO se muestra)"
  value       = { for k, p in aws_ssm_parameter.api_keys : k => p.name }
}

output "lambda_function_names" {
  description = "Nombres de las funciones Lambda (para aws lambda invoke y aws logs tail)"
  value       = { for k, f in aws_lambda_function.this : k => f.function_name }
}

output "datalake_bucket_arn" {
  description = "ARN del bucket (se usará en las políticas de IAM de la Fase 3)"
  value       = aws_s3_bucket.datalake.arn
}
