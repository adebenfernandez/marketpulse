# Alarmas de CloudWatch: un email (vía el tema SNS de alertas) en cuanto una Lambda falla.
#
# Complementa al destino on-failure (lambda.tf): la alarma salta con el PRIMER error, también en
# invocaciones manuales (síncronas); el destino solo avisa cuando se agotan los reintentos de una
# invocación asíncrona, y su mensaje trae el error concreto.

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = local.lambda_functions

  alarm_name        = "${each.value}-errores"
  alarm_description = "La Lambda ${each.value} ha terminado con error (excepcion o timeout). Ver sus logs en CloudWatch."

  # Métrica que Lambda publica sola y gratis: nº de ejecuciones que acabaron en error
  namespace   = "AWS/Lambda"
  metric_name = "Errors"
  dimensions = {
    FunctionName = each.value
  }

  statistic           = "Sum" # errores sumados dentro de cada periodo
  period              = 300   # periodos de 5 minutos
  evaluation_periods  = 1     # basta UN periodo malo para saltar
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold" # >= 1 error

  # Casi siempre NO hay datos (la función corre 2 veces al día). Sin datos = todo bien: si no,
  # la alarma pasaría a "datos insuficientes" o, peor, a ALARM, cada pocos minutos
  treat_missing_data = "notBreaching"

  alarm_actions = [aws_sns_topic.alertas.arn] # al pasar a ALARM -> email
}
