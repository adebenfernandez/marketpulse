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

# Sin valor por defecto: cada despliegue pone el suyo en terraform.tfvars (ignorado por Git;
# plantilla en terraform.tfvars.example), porque el repositorio será público
variable "alert_email" {
  description = "Email que recibe las alertas del tema SNS (presupuesto, alarmas y fallos de Lambda)"
  type        = string
  sensitive   = true # Terraform lo oculta en el plan y en los logs: (sensitive value)
}

# El backend no admite variables, así que el bucket del state se repite aquí para dárselo al rol de
# despliegue (cicd). Mismo valor que en backend.hcl; va en terraform.tfvars (no es secreto)
variable "tfstate_bucket_name" {
  description = "Bucket del state de Terraform creado por infra/bootstrap"
  type        = string
}
