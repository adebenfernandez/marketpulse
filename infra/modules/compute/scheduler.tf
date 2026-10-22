# Programación diaria con EventBridge Scheduler: ingesta a las 06:00 UTC y transformación a las
# 06:30 UTC. Scheduler invoca la Lambda de forma ASÍNCRONA: deja el encargo y no espera.

locals {
  schedules = {
    # Expresión cron de 6 campos: minutos horas día-del-mes mes día-de-la-semana año.
    # "?" = "me da igual" (no se puede fijar a la vez día del mes y día de la semana)
    ingest    = "cron(0 6 * * ? *)"  # todos los días a las 06:00
    transform = "cron(30 6 * * ? *)" # todos los días a las 06:30: tiempo de sobra para la ingesta
  }
}

# --- Rol que asume Scheduler para invocar las Lambdas ---

data "aws_iam_policy_document" "scheduler_trust" {
  statement {
    sid     = "SchedulerAsumeElRol"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    # Contra el "confused deputy": solo Scheduler actuando para ESTA cuenta puede usar el rol
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${var.project}-scheduler"
  description        = "Rol con el que EventBridge Scheduler invoca las Lambdas de MarketPulse"
  assume_role_policy = data.aws_iam_policy_document.scheduler_trust.json
}

data "aws_iam_policy_document" "scheduler" {
  statement {
    sid     = "InvocarSoloNuestrasLambdas"
    effect  = "Allow"
    actions = ["lambda:InvokeFunction"]
    # Las dos funciones, por ARN exacto. El ARN se CONSTRUYE con el nombre en lugar de leerlo de
    # aws_lambda_function.this: si no, cada cambio en una Lambda (p. ej. código nuevo) deja este
    # data "pendiente" hasta el apply y el plan muestra un cambio falso en la política (Fase 5)
    resources = [
      for name in values(local.lambda_functions) :
      "arn:aws:lambda:${local.region}:${local.account_id}:function:${name}"
    ]
  }
}

resource "aws_iam_role_policy" "scheduler" {
  name   = "invocar-lambdas"
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.scheduler.json
}

# --- Las dos programaciones ---

resource "aws_scheduler_schedule" "daily" {
  for_each = local.schedules

  name                         = "${local.lambda_functions[each.key]}-diaria"
  description                  = "Ejecucion diaria de ${local.lambda_functions[each.key]}"
  schedule_expression          = each.value
  schedule_expression_timezone = "UTC" # la misma referencia que dt en bronze (D-009)
  state                        = "ENABLED"

  flexible_time_window {
    mode = "OFF" # a la hora exacta (con una ventana, Scheduler podría retrasarlo para repartir carga)
  }

  target {
    arn      = aws_lambda_function.this[each.key].arn
    role_arn = aws_iam_role.scheduler.arn

    # Reintentos de Scheduler si NO consigue entregar el encargo a Lambda (p. ej. limitación).
    # Los fallos DENTRO de la función los reintenta Lambda (ver lambda_async en lambda.tf)
    retry_policy {
      maximum_retry_attempts       = 3
      maximum_event_age_in_seconds = 3600 # pasada 1 hora, se descarta (ya no tiene sentido)
    }
    # Sin dead_letter_config: exige una cola SQS, fuera de la lista de servicios permitidos
  }
}
