variable "project" {
  description = "Nombre del proyecto: prefijo del tema, del presupuesto y de las alarmas"
  type        = string
}

variable "account_id" {
  description = "ID de la cuenta de AWS, para construir ARN sin escribirlo en el código"
  type        = string
}

variable "region" {
  description = "Región de AWS, para construir el ARN del tema"
  type        = string
}

variable "alert_email" {
  description = "Email que recibe las alertas del tema SNS"
  type        = string
  sensitive   = true
}

variable "lambda_function_names" {
  description = "Funciones Lambda que vigilan las alarmas, por clave (ingest, transform)"
  type        = map(string)
}
