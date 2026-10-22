# Despliegue continuo (CD) sin claves de AWS en GitHub (D-027).
#
# La SCP de la cuenta deniega crear un proveedor OIDC, así que GitHub Actions no puede asumir un
# rol. En su lugar, CodeBuild (que corre DENTRO de AWS con su propio rol) lee el repositorio y
# recibe los avisos de push a través de esta conexión de CodeConnections.

# --- Conexión con GitHub ---
# Terraform la crea en estado PENDING: es solo la "solicitud". Para que pase a AVAILABLE, Alberto
# tiene que completar el apretón de manos (handshake) en la consola de AWS: iniciar sesión en
# GitHub e instalar la GitHub App "AWS Connector for GitHub" SOLO para el repositorio marketpulse.
# Terraform no puede hacer ese paso porque es un consentimiento de la cuenta de GitHub.
resource "aws_codeconnections_connection" "github" {
  name          = "${var.project}-github" # único en la cuenta; cambiarlo crearía otra conexión
  provider_type = "GitHub"
}
