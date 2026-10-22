# Valores que Terraform muestra al terminar (y que se consultan con `terraform output`).
# Mismos nombres que antes de los módulos: el README y los comandos de las fases anteriores siguen
# valiendo. Ahora cada valor sale del módulo que lo gestiona.

output "datalake_bucket_name" {
  description = "Nombre del bucket del data lake"
  value       = module.storage.bucket_name
}

output "datalake_bucket_arn" {
  description = "ARN del bucket del data lake"
  value       = module.storage.bucket_arn
}

output "api_key_parameter_names" {
  description = "Nombres de los parámetros de SSM con las claves de API (el valor NO se muestra)"
  value       = module.compute.api_key_parameter_names
}

output "lambda_function_names" {
  description = "Nombres de las funciones Lambda (para aws lambda invoke y aws logs tail)"
  value       = module.compute.lambda_function_names
}

output "athena_workgroup" {
  description = "Workgroup de Athena para todas las consultas de MarketPulse"
  value       = module.analytics.athena_workgroup
}

output "github_connection_status" {
  description = "Estado de la conexión con GitHub: PENDING hasta autorizarla en la consola"
  value       = module.cicd.github_connection_status
}

output "deploy_project_name" {
  description = "Proyecto de CodeBuild que despliega en cada push a main"
  value       = module.cicd.deploy_project_name
}
