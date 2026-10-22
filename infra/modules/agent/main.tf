# Rol de SOLO LECTURA del agente text-to-SQL (Fase 7, paso 7.5, D-033).
#
# El agente se ejecuta en local (Docker) y necesita credenciales de AWS para consultar Athena.
# No hay usuarios de IAM ni OIDC (D-001, D-027), y las claves permanentes están prohibidas, así que:
#   1. Alberto entra con `aws login` (rol temporal de administración, 12 h).
#   2. Con ese rol se "pone" ESTE rol (sts:AssumeRole) y recibe credenciales que caducan en 1 h
#      (al encadenar roles, AWS limita la sesión a 1 h como máximo).
#   3. Esas credenciales, y solo esas, se pasan al contenedor.
# Si el contenedor se ve comprometido, quien lo controle solo puede LEER los datos de gold durante
# menos de una hora: ni escribir en el data lake, ni tocar el catálogo, ni salir del workgroup.
#
# Es la SEGUNDA barrera contra SQL peligrosa (la primera es el validador, agent/guard.py): aunque
# un DROP TABLE se colara, Glue lo rechazaría porque el rol no tiene glue:DeleteTable (y su techo
# tampoco, D-032).

locals {
  glue_catalog_resources = [
    "arn:aws:glue:${var.region}:${var.account_id}:catalog",
    "arn:aws:glue:${var.region}:${var.account_id}:database/${var.project}",
    "arn:aws:glue:${var.region}:${var.account_id}:table/${var.project}/*",
  ]
  athena_workgroup_arn = "arn:aws:athena:${var.region}:${var.account_id}:workgroup/${var.athena_workgroup}"
}

# --- 1. Confianza: QUIÉN puede ponerse el rol -> solo el rol de Alberto en esta cuenta ---

data "aws_iam_policy_document" "agent_trust" {
  statement {
    sid     = "AlbertoAsumeElRol"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = [var.trusted_principal_arn] # un rol concreto, no toda la cuenta
    }
  }
}

resource "aws_iam_role" "agent" {
  name                 = "${var.project}-agent"
  description          = "Solo lectura para el agente text-to-SQL: Glue, Athena y gold (D-033)"
  assume_role_policy   = data.aws_iam_policy_document.agent_trust.json
  max_session_duration = 3600                         # 1 h: el máximo real al encadenar roles
  permissions_boundary = var.permissions_boundary_arn # techo obligatorio (D-028)
}

# --- 2. Permisos: QUÉ puede hacer -> leer y consultar, nada más ---

data "aws_iam_policy_document" "agent" {
  statement {
    sid       = "LeerElCatalogo"
    effect    = "Allow"
    actions   = ["glue:GetDatabase", "glue:GetTable", "glue:GetTables"] # ni Create, ni Update, ni Delete
    resources = local.glue_catalog_resources
  }

  statement {
    sid    = "ConsultarEnSuWorkgroup"
    effect = "Allow"
    # Las 4 llamadas de common/athena.py (run_query). Solo en el workgroup marketpulse, que tiene el
    # límite de 100 MB por consulta y fuerza la ubicación de los resultados (paso 4.3)
    actions = [
      "athena:StartQueryExecution", "athena:GetQueryExecution",
      "athena:GetQueryResults", "athena:StopQueryExecution",
    ]
    resources = [local.athena_workgroup_arn]
  }

  statement {
    sid       = "UbicacionDelBucket"
    effect    = "Allow"
    actions   = ["s3:GetBucketLocation"] # Athena la pide antes de escribir los resultados
    resources = [var.bucket_arn]
  }

  statement {
    sid       = "ListarSoloGoldYResultados"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [var.bucket_arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["gold/*", "${var.athena_results_prefix}*"] # ni bronze/ ni silver/
    }
  }

  statement {
    sid       = "LeerGold"
    effect    = "Allow"
    actions   = ["s3:GetObject"] # solo leer: las tablas y vistas de Athena están sobre gold/
    resources = ["${var.bucket_arn}/gold/*"]
  }

  statement {
    sid    = "ResultadosDeSusConsultas"
    effect = "Allow"
    # Athena escribe el CSV del resultado con las credenciales de quien lanza la consulta
    actions = [
      "s3:GetObject", "s3:PutObject",
      "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts",
    ]
    resources = ["${var.bucket_arn}/${var.athena_results_prefix}*"]
  }
}

resource "aws_iam_role_policy" "agent" {
  name   = "leer-datos-marketpulse"
  role   = aws_iam_role.agent.id
  policy = data.aws_iam_policy_document.agent.json
}
