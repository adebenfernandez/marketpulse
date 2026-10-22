# Permissions boundary (límite de permisos): el TECHO de los roles de la carga de trabajo
# (las dos Lambdas y el Scheduler). Un rol con este límite solo puede hacer lo que esté A LA VEZ
# en su propia política y aquí; aunque alguien le añadiera "Action": "*", seguiría sin poder salir
# de esta lista.
#
# Para qué (D-028): el rol de despliegue de CodeBuild (paso 6.5b) podrá crear y modificar roles
# marketpulse-* SOLO si llevan este límite puesto, y tendrá denegado tocar esta política. Así no
# puede "fabricarse una llave maestra" dándole permisos de administrador a una Lambda.
#
# El techo cubre lo que hacen los roles de la carga de trabajo (iam.tf y scheduler.tf de compute,
# y desde la Fase 7 el rol de solo lectura del agente), con las mismas acciones; los prefijos y
# las condiciones finas siguen en la política de cada rol.
#
# Fase 7 (paso 7.4, D-032): se añaden las consultas de SOLO LECTURA del agente text-to-SQL:
# leer el catálogo de Glue de la base marketpulse, lanzar consultas en el workgroup marketpulse y
# escribir/leer sus resultados en athena-results/. Ninguna acción de Glue que cree, cambie o borre,
# así que ningún rol con este techo puede hacer un DROP TABLE aunque su política lo permitiera.

locals {
  # Patrones construidos con el proyecto, la cuenta y la región: ningún "Resource": "*"
  lambda_log_groups = "arn:aws:logs:${var.region}:${var.account_id}:log-group:/aws/lambda/${var.project}-*"
  ssm_parameters    = "arn:aws:ssm:${var.region}:${var.account_id}:parameter/${var.project}/*"
  lambda_functions  = "arn:aws:lambda:${var.region}:${var.account_id}:function:${var.project}-*"

  # Glue: una acción sobre una tabla necesita permiso también en sus "antepasados" (la base y el
  # catálogo), según la guía de Athena "Configure access to databases and tables"
  glue_catalog_resources = [
    "arn:aws:glue:${var.region}:${var.account_id}:catalog",
    "arn:aws:glue:${var.region}:${var.account_id}:database/${var.project}",
    "arn:aws:glue:${var.region}:${var.account_id}:table/${var.project}/*",
  ]
  athena_workgroup = "arn:aws:athena:${var.region}:${var.account_id}:workgroup/${var.project}"
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
    sid    = "ListarElDataLake"
    effect = "Allow"
    # GetBucketLocation: Athena lo pide para escribir los resultados (política AmazonAthenaFullAccess)
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
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

  # --- Fase 7: consultas de solo lectura del agente text-to-SQL (D-032) ---

  statement {
    sid    = "LeerElCatalogo"
    effect = "Allow"
    actions = [
      "glue:GetDatabase", "glue:GetTable", "glue:GetTables",
      "glue:GetPartition", "glue:GetPartitions", "glue:BatchGetPartition",
    ]
    resources = local.glue_catalog_resources
  }

  statement {
    sid    = "ConsultarConAthena"
    effect = "Allow"
    actions = [
      "athena:StartQueryExecution", "athena:GetQueryExecution", "athena:GetQueryResults",
      "athena:StopQueryExecution", "athena:GetWorkGroup",
    ]
    resources = [local.athena_workgroup]
  }

  statement {
    sid    = "ResultadosDeAthena"
    effect = "Allow"
    # Athena escribe el resultado de cada consulta con las credenciales de quien la lanza
    actions = [
      "s3:GetObject", "s3:PutObject",
      "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts",
    ]
    resources = ["${var.bucket_arn}/athena-results/*"]
  }
}

resource "aws_iam_policy" "workload_boundary" {
  name        = "${var.project}-boundary"
  description = "Techo de permisos de los roles de las Lambdas y del Scheduler de MarketPulse (D-028)"
  # Nota: la descripción NO se cambia al añadir el agente; en una política de IAM, cambiarla
  # obliga a reemplazarla (destroy + create), y el techo está puesto en 3 roles
  policy = data.aws_iam_policy_document.workload_boundary.json
}
