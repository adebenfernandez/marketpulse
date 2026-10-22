# Proveedores que usa este módulo. La VERSIÓN la fija el módulo raíz (infra/versions.tf y el lock
# file): aquí solo se dice de dónde viene "aws", y el módulo hereda el proveedor ya configurado
# (región y default_tags) del raíz.
terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}
