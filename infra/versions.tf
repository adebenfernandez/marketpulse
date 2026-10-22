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

  # Dónde se guarda el state: en S3 (bucket creado por infra/bootstrap/), no en el disco local.
  # Un bloque backend NO admite variables (Terraform lo lee antes que nada), así que el nombre del
  # bucket se pasa aparte en `terraform init -backend-config=backend.hcl` ("configuración
  # parcial"): cada despliegue desde cero tiene su propio bucket con otro sufijo aleatorio.
  backend "s3" {
    key          = "marketpulse/terraform.tfstate" # ruta del state dentro del bucket
    region       = "eu-north-1"                    # tampoco admite var.region
    encrypt      = true                            # el state y el candado se escriben cifrados
    use_lockfile = true                            # candado nativo de S3 (<key>.tflock), sin DynamoDB
  }
}
