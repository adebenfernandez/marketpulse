# Valores configurables. Tienen un valor por defecto, así que no hace falta pasarlos.

variable "region" {
  description = "Región de AWS del proyecto (fija en la cuenta de la nueva experiencia)"
  type        = string
  default     = "eu-north-1"
}

variable "project" {
  description = "Nombre del proyecto: se usa en nombres y en la etiqueta project"
  type        = string
  default     = "marketpulse"
}
