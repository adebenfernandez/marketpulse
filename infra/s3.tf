# Bucket del data lake: aquí vivirán las capas bronze/, silver/ y gold/ (como prefijos).

resource "aws_s3_bucket" "datalake" {
  # El nombre de un bucket es único en TODO el mundo. Con bucket_prefix, Terraform añade
  # un sufijo aleatorio (p. ej. marketpulse-datalake-20261020...). Así no hace falta poner
  # el número de cuenta en el nombre, y el repositorio público no lo muestra.
  bucket_prefix = "${var.project}-datalake-"

  # false = Terraform se NIEGA a borrar el bucket si tiene objetos dentro (protección
  # contra un `terraform destroy` por error). Para borrarlo habría que vaciarlo antes.
  force_destroy = false
}

# 1) Bloqueo de acceso público: las cuatro llaves cerradas. Aunque alguien añadiera por error
#    una política o una ACL pública, S3 la ignoraría o la rechazaría.
resource "aws_s3_bucket_public_access_block" "datalake" {
  bucket = aws_s3_bucket.datalake.id # referencia al bucket de arriba (Terraform deduce el orden)

  block_public_acls       = true # rechaza ACL públicas nuevas
  ignore_public_acls      = true # ignora las ACL públicas que ya existieran
  block_public_policy     = true # rechaza políticas de bucket que den acceso público
  restrict_public_buckets = true # si hubiera una política pública, solo AWS y la cuenta acceden
}

# 2) Cifrado en reposo: cada objeto se guarda cifrado con claves gestionadas por S3 (SSE-S3).
#    Sin coste adicional. La alternativa con KMS (SSE-KMS) cobra por clave y por petición.
resource "aws_s3_bucket_server_side_encryption_configuration" "datalake" {
  bucket = aws_s3_bucket.datalake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256" # AES256 = SSE-S3
    }
  }
}

# 3) Propiedad de objetos: desactiva las ACL (el sistema antiguo de permisos por objeto).
#    Todos los objetos son del dueño del bucket y los permisos se controlan solo con IAM.
resource "aws_s3_bucket_ownership_controls" "datalake" {
  bucket = aws_s3_bucket.datalake.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# 4) Política del bucket "solo HTTPS": DENIEGA cualquier petición que no llegue cifrada en
#    tránsito (TLS). No da permisos a nadie: solo los quita. Los permisos siguen viniendo de IAM.
data "aws_iam_policy_document" "datalake_tls_only" {
  # Un bloque "data" no crea nada en AWS: solo genera el JSON de la política a partir de HCL,
  # que es más fácil de leer y Terraform comprueba que esté bien formado.
  statement {
    sid     = "DenegarSinHTTPS"
    effect  = "Deny"
    actions = ["s3:*"] # todas las acciones de S3...

    principals {
      type        = "*" # ...de cualquiera (incluido el propietario)...
      identifiers = ["*"]
    }

    resources = [
      aws_s3_bucket.datalake.arn,        # ...sobre el bucket (listar, configurar)...
      "${aws_s3_bucket.datalake.arn}/*", # ...y sobre todos sus objetos...
    ]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport" # ...cuando la conexión NO es HTTPS
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "datalake" {
  bucket = aws_s3_bucket.datalake.id
  policy = data.aws_iam_policy_document.datalake_tls_only.json

  # Si se aplicaran a la vez, S3 podría evaluar la política antes de que exista el bloqueo de
  # acceso público. Forzamos el orden: primero el bloqueo, después la política.
  depends_on = [aws_s3_bucket_public_access_block.datalake]
}
