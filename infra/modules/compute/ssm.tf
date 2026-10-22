# Claves de API en SSM Parameter Store, como SecureString (cifradas con KMS).
#
# Terraform crea el "cajón" (nombre, tipo, cifrado y etiquetas) con un valor de RELLENO, y la
# clave real la escribe Alberto con la AWS CLI. Así el secreto nunca pasa por Terraform: ni por
# el código, ni por el plan, ni por el state (que guarda todos los valores en texto plano).
# Las Lambdas reciben solo el NOMBRE del parámetro y leen el valor al ejecutarse.

locals {
  # Clave del mapa -> descripción. El nombre en SSM será /marketpulse/<clave>
  api_key_parameters = {
    coingecko_api_key    = "Clave Demo de la API de CoinGecko (cabecera x-cg-demo-api-key)"
    alphavantage_api_key = "Clave gratuita de la API de Alpha Vantage (25 peticiones al día)"
  }
}

resource "aws_ssm_parameter" "api_keys" {
  # for_each crea un recurso por cada elemento del mapa: api_keys["coingecko_api_key"] y
  # api_keys["alphavantage_api_key"]. Mismo bloque de código para las dos claves
  for_each = local.api_key_parameters

  # Nombre jerárquico (como una carpeta): permite dar permisos a /marketpulse/... y nada más
  name        = "/${var.project}/${each.key}"
  description = each.value
  type        = "SecureString" # cifrado con KMS; sin key_id usa la clave gestionada alias/aws/ssm
  tier        = "Standard"     # sin coste (Advanced cobra por parámetro y por llamada)

  # Valor de relleno. Es lo único que llega al state: no es un secreto
  value = "PENDIENTE-se-escribe-con-la-cli"

  lifecycle {
    # Después de crearlo, Terraform IGNORA los cambios del valor. Cuando Alberto escriba la clave
    # real con la CLI, el siguiente `terraform plan` no intentará volver a poner el relleno
    ignore_changes = [value]
  }
}
