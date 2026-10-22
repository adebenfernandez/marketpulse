# Bucket del state de Terraform de MarketPulse.
#
# Las mismas protecciones que el data lake (s3.tf) y dos más, propias de un state:
#   - Versionado: cada escritura del state guarda la anterior como "versión no actual". Si un
#     apply o una migración lo estropea, se recupera la versión buena (recomendación oficial del
#     backend S3 de Terraform).
#   - prevent_destroy: Terraform se niega a borrar el bucket aunque se lo pidan.

variable "region" {
  description = "Región de AWS del proyecto (fija en la cuenta de la nueva experiencia)"
  type        = string
  default     = "eu-north-1"
}

variable "project" {
  description = "Nombre del proyecto: se usa en nombres y en la etiqueta project"
  type        = string
  default     = "marketpulse"
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      project    = var.project
      managed_by = "terraform"
      stack      = "bootstrap" # para distinguirlo de lo que gestiona infra/
    }
  }
}

resource "aws_s3_bucket" "tfstate" {
  bucket_prefix = "${var.project}-tfstate-" # nombre único sin el número de cuenta (como el data lake)
  force_destroy = false                     # nunca borrar un bucket con states dentro

  lifecycle {
    prevent_destroy = true # un `terraform destroy` aquí fallaría con un error, a propósito
  }
}

# 1) Versionado: imprescindible para poder volver a un state anterior
resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  versioning_configuration {
    status = "Enabled"
  }
}

# 2) Bloqueo de acceso público: las cuatro llaves cerradas (el state describe toda la infraestructura)
resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

# 3) Cifrado en reposo SSE-S3 (sin coste). El backend añade `encrypt = true` en cada escritura
resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# 4) Sin ACL: todo es del dueño del bucket y los permisos van solo por IAM
resource "aws_s3_bucket_ownership_controls" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# 5) Solo HTTPS: deniega cualquier petición sin cifrar en tránsito
data "aws_iam_policy_document" "tfstate_tls_only" {
  statement {
    sid     = "DenegarSinHTTPS"
    effect  = "Deny"
    actions = ["s3:*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    resources = [
      aws_s3_bucket.tfstate.arn,
      "${aws_s3_bucket.tfstate.arn}/*",
    ]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "tfstate" {
  bucket     = aws_s3_bucket.tfstate.id
  policy     = data.aws_iam_policy_document.tfstate_tls_only.json
  depends_on = [aws_s3_bucket_public_access_block.tfstate]
}

# 6) Ciclo de vida: el versionado guarda TODAS las versiones para siempre si no se limpia.
#    Cada plan/apply crea y borra el candado (.tflock), y cada apply escribe un state nuevo, así
#    que se acumulan versiones antiguas y "marcadores de borrado" (delete markers).
resource "aws_s3_bucket_lifecycle_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    id     = "limpiar-versiones-antiguas"
    status = "Enabled"

    filter {} # todo el bucket

    # Las versiones NO actuales se borran 90 días después de dejar de serlo: margen de sobra para
    # darse cuenta de un state roto y volver atrás. La versión actual no se toca nunca
    noncurrent_version_expiration {
      noncurrent_days = 90
    }

    # Cuando un objeto borrado (p. ej. un .tflock) ya no tiene versiones detrás, su marcador de
    # borrado se queda solo y no sirve para nada: S3 lo elimina
    expiration {
      expired_object_delete_marker = true
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }

  # S3 exige que el versionado esté configurado antes que las reglas de versiones
  depends_on = [aws_s3_bucket_versioning.tfstate]
}
