output "bucket_name" {
  description = "Nombre del bucket del data lake"
  value       = aws_s3_bucket.datalake.bucket
}

output "bucket_arn" {
  description = "ARN del bucket (para las políticas de IAM de compute)"
  value       = aws_s3_bucket.datalake.arn
}

output "athena_results_prefix" {
  description = "Prefijo de los resultados de Athena, con borrado a los 7 días (lo usa analytics)"
  value       = local.athena_results_prefix
}
