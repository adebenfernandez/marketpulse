# Configuración del proveedor de AWS: en qué región trabajar y qué etiquetas poner a todo.
#
# Las credenciales NO se escriben aquí. Terraform las busca igual que la AWS CLI:
#   - En local: perfil indicado en la variable de entorno AWS_PROFILE (marketpulse, de `aws login`).
#   - En GitHub Actions (Fase 6): credenciales temporales obtenidas con OIDC.
provider "aws" {
  region = var.region

  # Estas etiquetas se añaden automáticamente a TODOS los recursos que cree este proveedor
  default_tags {
    tags = {
      project    = var.project
      managed_by = "terraform"
    }
  }
}
