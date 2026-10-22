# Presupuesto mensual de MarketPulse: 5 USD con avisos al 50, 80 y 100 % del gasto REAL.
#
# Se creó A MANO en la Fase 0 (D-004, D-005) y se trajo a Terraform en la Fase 5 con un bloque
# import (imports.tf, ya borrado). Al importarlo, el inventario del paso 5.1 encontró dos diferencias con lo
# que se había decidido, que este código CORRIGE (el plan las muestra como cambios):
#   1. Faltaba la alerta del 100 %.
#   2. No había filtro: los créditos (100 USD del plan gratuito) se restaban del gasto, así que el
#      gasto neto se quedaría en 0 y las alertas no saltarían nunca mientras quedaran créditos.
#
# Budgets AVISA pero no frena, y con horas de retraso. Budgets sin "acciones" es gratis.

resource "aws_budgets_budget" "mensual" {
  name         = "${var.project}-mensual"
  budget_type  = "COST" # dinero (la alternativa, USAGE, mide horas o GB)
  limit_amount = "5.0"  # como texto: así lo devuelve la API de Budgets
  limit_unit   = "USD"
  time_unit    = "MONTHLY" # el gasto se pone a cero el día 1 de cada mes

  # Cómo se suma el gasto: coste "sin combinar" (lo que cuesta cada uso, sin repartos entre cuentas)
  metrics = ["UnblendedCost"]

  # Sobre qué "vista de facturación" se mide: la principal de la cuenta (la que asignó la consola).
  # Se escribe para que el plan no proponga quitarla (la importación la trae y, si no está en el
  # código, Terraform querría dejarla a null)
  billing_view_arn = "arn:aws:billing::${var.account_id}:billingview/primary"

  # Qué gasto cuenta: TODO menos los créditos (D-005). Con la API actual de Budgets, un presupuesto
  # con "metrics" se filtra con filter_expression (el antiguo bloque cost_types no se puede usar a
  # la vez). RECORD_TYPE es el "tipo de cargo" que muestra la consola (Usage, Credit, Tax...)
  filter_expression {
    not {
      dimensions {
        key    = "RECORD_TYPE"
        values = ["Credit"]
      }
    }
  }

  # Un aviso por umbral, siempre sobre el gasto REAL (ACTUAL) y al tema SNS (D-004), no por email
  # directo: la SCP de la cuenta impide verificar destinatarios de email de Budgets
  dynamic "notification" {
    for_each = [50, 80, 100]

    content {
      notification_type         = "ACTUAL"
      comparison_operator       = "GREATER_THAN"
      threshold                 = notification.value
      threshold_type            = "PERCENTAGE"
      subscriber_sns_topic_arns = [aws_sns_topic.alertas.arn]
    }
  }
}
