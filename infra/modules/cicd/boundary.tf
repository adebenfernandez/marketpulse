# Permissions boundary (límite de permisos): el TECHO de los roles de la carga de trabajo
# (las dos Lambdas y el Scheduler). Un rol con este límite solo puede hacer lo que esté A LA VEZ
# en su propia política y aquí; aunque alguien le añadiera "Action": "*", seguiría sin poder salir
# de esta lista.
#
# Para qué (D-028): el rol de despliegue de CodeBuild (paso 6.5b) podrá crear y modificar roles
# marketpulse-* SOLO si llevan este límite puesto, y tendrá denegado tocar esta política. Así no
# puede "fabricarse una llave maestra" dándole permisos de administrador a una Lambda.
#
# El techo cubre EXACTAMENTE lo que ya tienen hoy los tres roles (iam.tf y scheduler.tf de compute),
# con las mismas acciones; los prefijos y las condiciones finas siguen en sus políticas.

locals {
  # Patrones construidos con el proyecto, la cuenta y la región: ningún "Resource": "*"
  lambda_log_groups = "arn:aws:logs:${var.region}:${var.account_id}:log-group:/aws/lambda/${var.project}-*"
  ssm_parameters    = "arn:aws:ssm:${var.region}:${var.account_id}:parameter/${var.project}/*"
  lambda_functions  = "arn:aws:lambda:${var.region}:${var.account_id}:function:${var.project}-*"
}

data "aws_iam_policy_document" "workload_boundary" {
  statement {
    sid       = "LogsDeLasLambdas"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${local.lambda_log_groups}:*"]
  }

  statement {
    sid       = "ClavesDeApi"
    effect    = "Allow"
    actions   = ["ssm:GetParameters"]
    resources = [local.ssm_parameters]
  }

  statement {
    sid       = "ListarElDataLake"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [var.bucket_arn]
  }

  statement {
    sid     = "LeerYEscribirLasCapas"
    effect  = "Allow"
    actions = ["s3:GetObject", "s3:PutObject"] # nunca DeleteObject (D-018)
    resources = [
      "${var.bucket_arn}/bronze/*",
      "${var.bucket_arn}/silver/*",
      "${var.bucket_arn}/gold/*",
    ]
  }

  statement {
    sid       = "AvisarPorSns"
    effect    = "Allow"
    actions   = ["sns:Publish"]
    resources = [var.alertas_topic_arn]
  }

  statement {
    sid       = "InvocarNuestrasLambdas"
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"] # lo usa el rol del Scheduler
    resources = [local.lambda_functions]
  }
}

resource "aws_iam_policy" "workload_boundary" {
  name        = "${var.project}-boundary"
  description = "Techo de permisos de los roles de las Lambdas y del Scheduler de MarketPulse (D-028)"
  policy      = data.aws_iam_policy_document.workload_boundary.json
}
