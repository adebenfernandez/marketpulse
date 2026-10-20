# Qué versiones de Terraform y de proveedores acepta este código.
# Fijarlas evita que una actualización automática cambie el comportamiento sin avisar.
terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws" # proveedor oficial de AWS (registry.terraform.io)
      version = "~> 6.69"       # cualquier 6.x a partir de 6.69, pero nunca 7.0 (podría romper)
    }
  }
}
