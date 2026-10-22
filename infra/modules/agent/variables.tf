variable "project" {
  description = "Nombre del proyecto: prefijo del rol (marketpulse-agent)"
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
  description = "ARN del bucket del data lake: el agente lee gold/ y usa athena-results/"
  type        = string
}

variable "athena_results_prefix" {
  description = "Prefijo de los resultados de Athena dentro del bucket (athena-results/)"
  type        = string
}

variable "athena_workgroup" {
  description = "Workgroup de Athena en el que el agente puede lanzar consultas"
  type        = string
}

variable "permissions_boundary_arn" {
  description = "Techo de permisos (D-028, ampliado en D-032): el deployer solo crea roles con él"
  type        = string
}

variable "trusted_principal_arn" {
  description = "Rol que puede ponerse el rol del agente (el de Alberto, con aws login): sts:AssumeRole"
  type        = string
}
