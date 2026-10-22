variable "project" {
  description = "Nombre del proyecto: prefijo de funciones, roles, logs y parámetros"
  type        = string
}

variable "account_id" {
  description = "ID de la cuenta de AWS, para construir ARN sin escribirlo en el código"
  type        = string
}

variable "region" {
  description = "Región de AWS, para construir ARN"
  type        = string
}

variable "bucket_name" {
  description = "Bucket del data lake (variable de entorno MARKETPULSE_BUCKET de las Lambdas)"
  type        = string
}

variable "bucket_arn" {
  description = "ARN del bucket del data lake, para las políticas de IAM"
  type        = string
}

variable "alertas_topic_arn" {
  description = "Tema SNS de alertas: destino on-failure de las Lambdas"
  type        = string
}

variable "lambda_zip_path" {
  description = "Ruta del zip de las Lambdas (python scripts/build_lambda.py)"
  type        = string
}
