# Tema SNS de alertas: recibe los avisos del presupuesto (Budgets), de las alarmas de CloudWatch y
# del destino on-failure de las Lambdas, y los reenvía por email.
#
# Se creó A MANO en la Fase 0 (D-004) y se trajo a Terraform en la Fase 5 con bloques import
# (imports.tf): el código describe exactamente lo que ya existía, para que el plan no cambie nada.

locals {
  # ARN del tema CONSTRUIDO con datos ya conocidos. Las políticas lo usan en lugar de
  # aws_sns_topic.alertas.arn por el mismo motivo que en scheduler.tf (paso 5.2): si el tema tiene
  # cambios pendientes (p. ej. una etiqueta), las políticas que lo leen saldrían como cambio falso
  alertas_topic_arn = "arn:aws:sns:${local.region}:${local.account_id}:${var.project}-alertas"
}

resource "aws_sns_topic" "alertas" {
  name         = "${var.project}-alertas"
  display_name = "MarketPulse" # el remitente que se ve en los emails
  # Sin kms_master_key_id: sin cifrado, a propósito (D-004: los mensajes no son sensibles y con KMS
  # Budgets necesitaría permisos sobre la clave).
  # Sin el argumento "policy": la política se gestiona aparte, en aws_sns_topic_policy. Si se
  # pusiera en los dos sitios, cada uno intentaría imponer la suya en cada apply.
}

# --- Política de acceso del tema (de recurso: QUIÉN puede hacer QUÉ sobre este tema) ---

data "aws_iam_policy_document" "alertas" {
  # Mismos Version e Id que la política que generó la consola: si no, Terraform vería un cambio
  version   = "2008-10-17"
  policy_id = "__default_policy_ID"

  # 1) La sentencia POR DEFECTO que SNS pone a todo tema nuevo. Es la que deja publicar a las
  #    alarmas de CloudWatch (y a cualquier principal o servicio que actúe para ESTA cuenta).
  #    Si se quitara, las alarmas dejarían de avisar SIN dar ningún error. Se copia tal cual.
  statement {
    sid    = "__default_statement_ID"
    effect = "Allow"
    actions = [
      "SNS:GetTopicAttributes",
      "SNS:SetTopicAttributes",
      "SNS:AddPermission",
      "SNS:RemovePermission",
      "SNS:DeleteTopic",
      "SNS:Subscribe",
      "SNS:ListSubscriptionsByTopic",
      "SNS:Publish",
    ]
    resources = [local.alertas_topic_arn]

    principals {
      type        = "AWS"
      identifiers = ["*"] # "cualquiera"... pero solo si la condición de abajo se cumple
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceOwner" # ...el dueño del origen es esta cuenta
      values   = [local.account_id]
    }
  }

  # 2) La sentencia que añadimos en la Fase 0 (paso 0.3c): Budgets puede publicar, y solo para
  #    presupuestos de esta cuenta (contra el "confused deputy")
  statement {
    sid       = "PermitirBudgetsPublicar"
    effect    = "Allow"
    actions   = ["SNS:Publish"]
    resources = [local.alertas_topic_arn]

    principals {
      type        = "Service"
      identifiers = ["budgets.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:budgets::${local.account_id}:*"] # Budgets es global: ARN sin región
    }
  }
}

resource "aws_sns_topic_policy" "alertas" {
  arn    = aws_sns_topic.alertas.arn
  policy = data.aws_iam_policy_document.alertas.json
}

# --- Suscripción por email ---
# Ojo: SNS solo admite email de forma "parcial" en Terraform. Una suscripción nueva queda pendiente
# hasta que alguien pulsa el enlace del correo de confirmación, y mientras tanto Terraform no puede
# borrarla. La nuestra ya está confirmada, así que al importarla Terraform la gestiona por completo.
resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alertas.arn
  protocol  = "email"
  endpoint  = var.alert_email # fuera del código: el repositorio será público
}
