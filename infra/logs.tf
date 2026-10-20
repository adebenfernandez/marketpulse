# Grupos de logs de CloudWatch para las dos Lambdas, creados ANTES que las funciones.
#
# Si no existieran, Lambda los crearía sola la primera vez que escribe un log, pero con retención
# "para siempre" (coste creciente) y fuera de Terraform. Creándolos aquí: retención de 14 días
# (regla de costes de CLAUDE.md) y el rol de la Lambda NO necesita permiso logs:CreateLogGroup.

locals {
  # Nombre de cada función. Lambda escribe siempre en el grupo /aws/lambda/<nombre de la función>
  lambda_functions = {
    ingest    = "${var.project}-ingest"
    transform = "${var.project}-transform"
  }
}

resource "aws_cloudwatch_log_group" "lambda" {
  for_each = local.lambda_functions

  name              = "/aws/lambda/${each.value}"
  retention_in_days = 14 # después, CloudWatch borra los logs solo
}
