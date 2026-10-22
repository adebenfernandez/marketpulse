variable "project" {
  description = "Nombre del proyecto: prefijo de la conexión y del proyecto de CodeBuild"
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

variable "bucket_arn" {
  description = "ARN del bucket del data lake (techo de los permisos de S3)"
  type        = string
}

variable "alertas_topic_arn" {
  description = "Tema SNS de alertas (techo de sns:Publish)"
  type        = string
}

variable "tfstate_bucket_name" {
  description = "Bucket del state de Terraform (infra/bootstrap): el deployer lee y escribe el state"
  type        = string
}
