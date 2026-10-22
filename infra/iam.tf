# Roles de ejecución de las Lambdas: la "identidad" con la que corre cada función.
#
# Cada rol tiene dos políticas:
#   1. De CONFIANZA (assume_role_policy): QUIÉN puede ponerse el rol -> solo el servicio Lambda.
#   2. De PERMISOS (aws_iam_role_policy): QUÉ puede hacer quien lo lleva puesto.
# Un rol por función: la ingesta no puede tocar silver/gold y la transformación no puede leer las
# claves de API. Mínimo privilegio: ningún "Resource": "*"; todo apunta a ARN concretos.

# Datos de la cuenta y la región actuales, para construir los ARN sin escribir el número de cuenta
# en el código (el repositorio será público)
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.region
  bucket_arn = aws_s3_bucket.datalake.arn
}

# --- 1. Política de confianza (la misma para las dos funciones) ---

data "aws_iam_policy_document" "lambda_trust" {
  statement {
    sid     = "LambdaAsumeElRol"
    effect  = "Allow"
    actions = ["sts:AssumeRole"] # "ponerse" el rol y recibir credenciales temporales

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"] # solo el servicio Lambda, ninguna persona
    }
  }
}

resource "aws_iam_role" "lambda" {
  for_each = local.lambda_functions

  name               = "${each.value}-lambda" # marketpulse-ingest-lambda, marketpulse-transform-lambda
  description        = "Rol de ejecucion de la Lambda ${each.value}"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

# --- 2a. Permisos de la Lambda de INGESTA ---

data "aws_iam_policy_document" "ingest" {
  statement {
    sid     = "EscribirSusLogs"
    effect  = "Allow"
    actions = ["logs:CreateLogStream", "logs:PutLogEvents"]
    # Solo SU grupo de logs. El ":*" final son los "log streams" de dentro del grupo (uno por
    # entorno de ejecución, con nombres que genera Lambda): no se pueden conocer de antemano
    resources = ["${aws_cloudwatch_log_group.lambda["ingest"].arn}:*"]
  }

  statement {
    sid       = "LeerClavesDeApi"
    effect    = "Allow"
    actions   = ["ssm:GetParameters"]                         # la única llamada que hace common/ssm.py
    resources = [for p in aws_ssm_parameter.api_keys : p.arn] # los dos parámetros, por ARN exacto
    # Sin kms:Decrypt: la política de la clave aws/ssm ya lo permite a través de SSM (D-021)
  }

  statement {
    sid       = "ListarSoloBronze"
    effect    = "Allow"
    actions   = ["s3:ListBucket"] # upload_layers compara con lo que ya hay (ETag)
    resources = [local.bucket_arn]

    condition {
      test     = "StringLike"
      variable = "s3:prefix" # el Prefix que pide list_objects_v2
      values   = ["bronze/*"]
    }
  }

  statement {
    sid       = "EscribirSoloEnBronze"
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = ["${local.bucket_arn}/bronze/*"] # ni silver/, ni gold/, ni otro bucket
  }
  statement {
    sid       = "AvisarDeFallos"
    effect    = "Allow"
    actions   = ["sns:Publish"] # destino de fallo de la invocación asíncrona (lambda.tf)
    resources = [local.alertas_topic_arn]
  }
}

resource "aws_iam_role_policy" "ingest" {
  name   = "permisos-ingesta"
  role   = aws_iam_role.lambda["ingest"].id
  policy = data.aws_iam_policy_document.ingest.json
}

# --- 2b. Permisos de la Lambda de TRANSFORMACIÓN ---

data "aws_iam_policy_document" "transform" {
  statement {
    sid       = "EscribirSusLogs"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.lambda["transform"].arn}:*"]
  }

  statement {
    sid       = "ListarLasTresCapas"
    effect    = "Allow"
    actions   = ["s3:ListBucket"] # download_layer (bronze) y upload_layers (silver, gold)
    resources = [local.bucket_arn]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["bronze/*", "silver/*", "gold/*"]
    }
  }

  statement {
    sid       = "LeerBronze"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${local.bucket_arn}/bronze/*"] # lee bronze, pero NO puede escribir en él
  }

  statement {
    sid     = "EscribirSilverYGold"
    effect  = "Allow"
    actions = ["s3:PutObject"]
    resources = [
      "${local.bucket_arn}/silver/*",
      "${local.bucket_arn}/gold/*",
    ]
  }
  statement {
    sid       = "AvisarDeFallos"
    effect    = "Allow"
    actions   = ["sns:Publish"] # destino de fallo de la invocación asíncrona (lambda.tf)
    resources = [local.alertas_topic_arn]
  }
}

resource "aws_iam_role_policy" "transform" {
  name   = "permisos-transformacion"
  role   = aws_iam_role.lambda["transform"].id
  policy = data.aws_iam_policy_document.transform.json
}
