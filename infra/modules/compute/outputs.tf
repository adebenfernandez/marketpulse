output "lambda_function_names" {
  description = "Nombres de las funciones Lambda, por clave (ingest, transform)"
  # Del local, no del recurso: son nombres fijos, conocidos antes del apply. Así monitoring puede
  # usarlos en for_each sin depender de que las funciones existan
  value = local.lambda_functions
}

output "api_key_parameter_names" {
  description = "Nombres de los parámetros de SSM con las claves de API (el valor NO se muestra)"
  value       = { for k, p in aws_ssm_parameter.api_keys : k => p.name }
}
