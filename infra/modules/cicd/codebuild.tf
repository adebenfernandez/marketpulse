# Proyecto de CodeBuild que despliega MarketPulse en cada push a main (D-027).
#
# Flujo: push a main -> webhook de GitHub -> CodeBuild arranca un contenedor ARM efímero con el rol
# marketpulse-deployer -> ejecuta buildspec.yml (tests, zip, plan, guardia, apply).
# Ninguna clave de AWS sale de AWS: el contenedor recibe credenciales temporales del rol.

# Logs del despliegue con retención de 14 días (regla de costes de CLAUDE.md)
resource "aws_cloudwatch_log_group" "deploy" {
  name              = "/aws/codebuild/${local.deploy_project_name}"
  retention_in_days = 14
}

# Variables que Terraform necesita dentro de CodeBuild. terraform.tfvars no está en Git (lleva el
# email), así que el email se guarda en SSM como SecureString y CodeBuild lo inyecta como variable
# de entorno al arrancar (nunca aparece en el buildspec ni en el repositorio)
resource "aws_ssm_parameter" "alert_email" {
  name        = "/${var.project}/alert_email"
  description = "Email de las alertas de MarketPulse (lo lee CodeBuild como TF_VAR_alert_email)"
  type        = "SecureString" # dato personal: cifrado con la clave gestionada aws/ssm
  tier        = "Standard"
  value       = var.alert_email
}

resource "aws_codebuild_project" "deploy" {
  name          = local.deploy_project_name
  description   = "Despliegue de MarketPulse con Terraform en cada push a main (D-027)"
  service_role  = aws_iam_role.deployer.arn
  build_timeout = 20 # minutos: un despliegue normal tarda unos 5; si se cuelga, se corta y no gasta más

  # Nunca dos despliegues a la vez (el candado del state ya lo impediría, pero así ni se intenta)
  concurrent_build_limit = 1

  source {
    type            = "GITHUB"
    location        = var.github_repository_url
    buildspec       = "buildspec.yml" # el fichero de la raíz del repositorio
    git_clone_depth = 1               # solo el último commit: no hace falta el historial

    # Acceso a GitHub a través de la conexión de CodeConnections (sin tokens guardados)
    auth {
      type     = "CODECONNECTIONS"
      resource = aws_codeconnections_connection.github.arn
    }
  }
  source_version = "main"

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL" # arm1.small: 100 min/mes gratis (D-027)
    type                        = "ARM_CONTAINER"
    image                       = "aws/codebuild/amazonlinux-aarch64-standard:4.0" # AL2023 con Python 3.13
    image_pull_credentials_type = "CODEBUILD"

    environment_variable {
      name  = "TF_VAR_alert_email"
      type  = "PARAMETER_STORE" # CodeBuild lo lee de SSM con el rol del proyecto
      value = aws_ssm_parameter.alert_email.name
    }
    environment_variable {
      name  = "TF_VAR_tfstate_bucket_name"
      value = var.tfstate_bucket_name # no es secreto
    }
  }

  artifacts {
    type = "NO_ARTIFACTS" # el resultado del build es el despliegue, no un fichero
  }

  logs_config {
    cloudwatch_logs {
      group_name = aws_cloudwatch_log_group.deploy.name
      status     = "ENABLED"
    }
    s3_logs {
      status = "DISABLED"
    }
  }

  # Al crear el proyecto, CodeBuild comprueba que SU ROL puede usar la conexión: la política del rol
  # tiene que existir antes (si no, "User is not authorized to access connection", paso 6.6)
  depends_on = [aws_iam_role_policy.deployer]
}

# Webhook: GitHub avisa a CodeBuild de cada push, y CodeBuild solo arranca si es a main.
# Lo crea CodeBuild en el repositorio usando la conexión (la app tiene permiso sobre los hooks)
resource "aws_codebuild_webhook" "deploy" {
  project_name = aws_codebuild_project.deploy.name
  build_type   = "BUILD"

  filter_group {
    filter {
      type    = "EVENT"
      pattern = "PUSH"
    }
    filter {
      type    = "HEAD_REF"
      pattern = "^refs/heads/main$" # solo la rama main (un merge de un PR es un push a main)
    }
  }
}
