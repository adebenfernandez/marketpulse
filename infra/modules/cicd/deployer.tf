# Rol de despliegue: la identidad con la que CodeBuild ejecutará `terraform plan` y `apply` (D-028).
#
# Puede gestionar todo lo de MarketPulse, pero:
#   - solo recursos con nombre marketpulse-* (o los ARN exactos del proyecto): nada de "Resource": "*";
#   - solo puede crear o modificar roles de IAM que lleven el techo marketpulse-boundary, así que no
#     puede fabricar un rol de administrador (escalada de privilegios);
#   - tiene DENEGADO tocar su propio rol, el techo, el proyecto de CodeBuild y la conexión con GitHub.
#     Esos cambios (este módulo cicd) los aplica Alberto a mano.

locals {
  p    = var.project
  acct = var.account_id
  reg  = var.region

  deploy_project_name = "${var.project}-deploy" # el proyecto de CodeBuild del paso 6.6
  deploy_project_arn  = "arn:aws:codebuild:${var.region}:${var.account_id}:project/${local.deploy_project_name}"
  deployer_role_name  = "${var.project}-deployer"
  deployer_role_arn   = "arn:aws:iam::${var.account_id}:role/${local.deployer_role_name}"
  boundary_arn        = aws_iam_policy.workload_boundary.arn

  # La conexión con sus DOS nombres: el servicio se llamaba CodeStar Connections y ahora
  # CodeConnections. CodeBuild comprueba el acceso con las acciones antiguas (codestar-connections:*),
  # así que se permiten los dos prefijos sobre los dos formatos de ARN (paso 6.6)
  connection_arns = [
    aws_codeconnections_connection.github.arn,
    replace(aws_codeconnections_connection.github.arn, ":codeconnections:", ":codestar-connections:"),
  ]
  connection_use_actions = [
    "codeconnections:GetConnection", "codeconnections:GetConnectionToken",
    "codeconnections:UseConnection", "codeconnections:ListTagsForResource",
    "codestar-connections:GetConnection", "codestar-connections:GetConnectionToken",
    "codestar-connections:UseConnection", "codestar-connections:ListTagsForResource",
  ]

  tfstate_bucket_arn = "arn:aws:s3:::${var.tfstate_bucket_name}"
  state_key          = "marketpulse/terraform.tfstate" # el mismo que el backend de infra/versions.tf

  # Roles que el deployer puede gestionar (todos con el techo) y "pasar" a Lambda y a Scheduler
  workload_roles = "arn:aws:iam::${var.account_id}:role/${var.project}-*"
  passable_roles = [
    "arn:aws:iam::${var.account_id}:role/${var.project}-ingest-lambda",
    "arn:aws:iam::${var.account_id}:role/${var.project}-transform-lambda",
    "arn:aws:iam::${var.account_id}:role/${var.project}-scheduler",
  ]
}

# --- Confianza: solo CodeBuild, y solo desde NUESTRO proyecto de esta cuenta ---

data "aws_iam_policy_document" "deployer_trust" {
  statement {
    sid     = "CodeBuildAsumeElRol"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["codebuild.amazonaws.com"]
    }

    # Contra el "confused deputy": ni otra cuenta ni otro proyecto de CodeBuild pueden usarlo
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [var.account_id]
    }
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = [local.deploy_project_arn]
    }
  }
}

resource "aws_iam_role" "deployer" {
  name               = local.deployer_role_name
  description        = "Rol con el que CodeBuild despliega MarketPulse con Terraform (D-028)"
  assume_role_policy = data.aws_iam_policy_document.deployer_trust.json
}

# --- Permisos, por bloques ---

data "aws_iam_policy_document" "deployer" {
  # 1) State de Terraform (D-025): leer y escribir el state y el candado, nada más
  statement {
    sid       = "StateListar"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [local.tfstate_bucket_arn]
  }
  statement {
    sid       = "StateLeerEscribir"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${local.tfstate_bucket_arn}/${local.state_key}"]
  }
  statement {
    sid       = "StateCandado"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${local.tfstate_bucket_arn}/${local.state_key}.tflock"]
  }

  # 2) Bucket del data lake: su CONFIGURACIÓN (no sus datos) y los resultados de Athena (vistas)
  statement {
    sid    = "DataLakeConfiguracion"
    effect = "Allow"
    actions = [
      "s3:ListBucket", "s3:GetBucket*", "s3:PutBucket*", "s3:DeleteBucketPolicy",
      "s3:GetAccelerateConfiguration", "s3:GetLifecycleConfiguration", "s3:PutLifecycleConfiguration",
      "s3:GetReplicationConfiguration", "s3:GetEncryptionConfiguration", "s3:PutEncryptionConfiguration",
      "s3:CreateBucket",
    ]
    resources = [var.bucket_arn]
  }
  statement {
    sid       = "ResultadosDeAthena"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload"]
    resources = ["${var.bucket_arn}/athena-results/*"]
  }

  # 3) Lambda: las funciones marketpulse-* y la capa pública de AWS SDK for pandas
  statement {
    sid    = "Lambdas"
    effect = "Allow"
    actions = [
      "lambda:Get*", "lambda:List*", "lambda:CreateFunction", "lambda:DeleteFunction",
      "lambda:UpdateFunctionCode", "lambda:UpdateFunctionConfiguration",
      "lambda:PutFunctionEventInvokeConfig", "lambda:UpdateFunctionEventInvokeConfig",
      "lambda:DeleteFunctionEventInvokeConfig", "lambda:TagResource", "lambda:UntagResource",
    ]
    resources = ["arn:aws:lambda:${local.reg}:${local.acct}:function:${local.p}-*"]
  }
  statement {
    sid       = "CapaDePandas"
    effect    = "Allow"
    actions   = ["lambda:GetLayerVersion"]
    resources = ["arn:aws:lambda:${local.reg}:336392948345:layer:AWSSDKPandas-Python313-Arm64:*"]
  }

  # 4) IAM: leer los roles del proyecto y el techo
  statement {
    sid    = "IamLeer"
    effect = "Allow"
    actions = [
      "iam:GetRole", "iam:GetRolePolicy", "iam:ListRolePolicies", "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole", "iam:ListRoleTags",
    ]
    resources = [local.workload_roles]
  }
  statement {
    sid       = "IamLeerTecho"
    effect    = "Allow"
    actions   = ["iam:GetPolicy", "iam:GetPolicyVersion", "iam:ListPolicyVersions", "iam:ListPolicyTags"]
    resources = [local.boundary_arn]
  }
  # ...y modificarlos SOLO si llevan el techo puesto (administración delegada)
  statement {
    sid    = "IamEscribirConTecho"
    effect = "Allow"
    actions = [
      "iam:CreateRole", "iam:DeleteRole", "iam:UpdateRole", "iam:UpdateRoleDescription",
      "iam:UpdateAssumeRolePolicy", "iam:PutRolePolicy", "iam:DeleteRolePolicy",
      "iam:AttachRolePolicy", "iam:DetachRolePolicy", "iam:PutRolePermissionsBoundary",
    ]
    resources = [local.workload_roles]

    condition {
      test     = "StringEquals"
      variable = "iam:PermissionsBoundary"
      values   = [local.boundary_arn]
    }
  }
  statement {
    sid       = "IamEtiquetas"
    effect    = "Allow"
    actions   = ["iam:TagRole", "iam:UntagRole"] # TagRole no admite la condición del techo
    resources = [local.workload_roles]
  }
  # "Pasar" un rol = asignárselo a un servicio. Solo los 3 roles con techo y solo a Lambda o Scheduler
  statement {
    sid       = "IamPasarRoles"
    effect    = "Allow"
    actions   = ["iam:PassRole"]
    resources = local.passable_roles

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["lambda.amazonaws.com", "scheduler.amazonaws.com"]
    }
  }

  # 5) Logs (Lambdas y CodeBuild) y alarmas
  statement {
    sid    = "GruposDeLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup", "logs:DeleteLogGroup", "logs:PutRetentionPolicy",
      "logs:DeleteRetentionPolicy", "logs:ListTagsForResource", "logs:ListTagsLogGroup",
      "logs:TagResource", "logs:UntagResource", "logs:TagLogGroup", "logs:UntagLogGroup",
    ]
    resources = [
      "arn:aws:logs:${local.reg}:${local.acct}:log-group:/aws/lambda/${local.p}-*",
      "arn:aws:logs:${local.reg}:${local.acct}:log-group:/aws/codebuild/${local.p}-*",
    ]
  }
  statement {
    sid       = "ListarGruposDeLogs"
    effect    = "Allow"
    actions   = ["logs:DescribeLogGroups"] # se acota a los grupos de ESTA cuenta y región
    resources = ["arn:aws:logs:${local.reg}:${local.acct}:log-group:*"]
  }
  statement {
    sid       = "LogsDelPropioBuild"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${local.reg}:${local.acct}:log-group:/aws/codebuild/${local.deploy_project_name}:*"]
  }
  statement {
    sid    = "Alarmas"
    effect = "Allow"
    actions = [
      "cloudwatch:DescribeAlarms", "cloudwatch:PutMetricAlarm", "cloudwatch:DeleteAlarms",
      "cloudwatch:ListTagsForResource", "cloudwatch:TagResource", "cloudwatch:UntagResource",
    ]
    resources = ["arn:aws:cloudwatch:${local.reg}:${local.acct}:alarm:${local.p}-*"]
  }

  # 6) SSM: los "cajones" de las claves (D-021). El valor lo escribe Alberto con la CLI
  statement {
    sid    = "ParametrosSsm"
    effect = "Allow"
    actions = [
      "ssm:GetParameter", "ssm:GetParameters", "ssm:PutParameter", "ssm:DeleteParameter",
      "ssm:AddTagsToResource", "ssm:RemoveTagsFromResource", "ssm:ListTagsForResource",
    ]
    resources = ["arn:aws:ssm:${local.reg}:${local.acct}:parameter/${local.p}/*"]
  }
  # EXCEPCIÓN aprobada por Alberto (paso 6.7): Terraform lee los metadatos de cada parámetro con
  # ssm:DescribeParameters, y AWS solo autoriza esa acción sobre TODOS los parámetros de la cuenta y
  # la región (no admite acotar por nombre). Solo lista nombres, tipos y descripciones: los VALORES
  # siguen necesitando GetParameter, limitado a /marketpulse/* en la sentencia de arriba
  statement {
    sid       = "MetadatosSsm"
    effect    = "Allow"
    actions   = ["ssm:DescribeParameters"]
    resources = ["arn:aws:ssm:${local.reg}:${local.acct}:*"]
  }

  # 7) SNS: el tema de alertas y su suscripción
  statement {
    sid    = "TemaDeAlertas"
    effect = "Allow"
    actions = [
      "sns:CreateTopic", "sns:DeleteTopic", "sns:GetTopicAttributes", "sns:SetTopicAttributes",
      "sns:ListTagsForResource", "sns:TagResource", "sns:UntagResource", "sns:Subscribe",
      "sns:Unsubscribe", "sns:GetSubscriptionAttributes", "sns:SetSubscriptionAttributes",
      "sns:ListSubscriptionsByTopic",
    ]
    resources = [var.alertas_topic_arn, "${var.alertas_topic_arn}:*"] # el tema y su suscripción
  }

  # 8) Budgets: el presupuesto mensual
  statement {
    sid    = "Presupuesto"
    effect = "Allow"
    actions = [
      "budgets:ViewBudget", "budgets:ModifyBudget", "budgets:ListTagsForResource",
      "budgets:TagResource", "budgets:UntagResource",
    ]
    resources = ["arn:aws:budgets::${local.acct}:budget/${local.p}-mensual"]
  }

  # 9) Glue Data Catalog y Athena (tablas, workgroup y las consultas que despliegan las vistas)
  statement {
    sid    = "Catalogo"
    effect = "Allow"
    actions = [
      "glue:GetDatabase", "glue:CreateDatabase", "glue:UpdateDatabase", "glue:DeleteDatabase",
      "glue:GetTable", "glue:GetTables", "glue:CreateTable", "glue:UpdateTable", "glue:DeleteTable",
      "glue:GetTags", "glue:TagResource", "glue:UntagResource",
    ]
    resources = [
      "arn:aws:glue:${local.reg}:${local.acct}:catalog",
      "arn:aws:glue:${local.reg}:${local.acct}:database/${local.p}",
      "arn:aws:glue:${local.reg}:${local.acct}:table/${local.p}/*",
    ]
  }
  statement {
    sid    = "Athena"
    effect = "Allow"
    actions = [
      "athena:GetWorkGroup", "athena:CreateWorkGroup", "athena:UpdateWorkGroup", "athena:DeleteWorkGroup",
      "athena:ListTagsForResource", "athena:TagResource", "athena:UntagResource",
      "athena:StartQueryExecution", "athena:GetQueryExecution", "athena:GetQueryResults",
      "athena:StopQueryExecution",
    ]
    resources = ["arn:aws:athena:${local.reg}:${local.acct}:workgroup/${local.p}"]
  }

  # 10) EventBridge Scheduler: las programaciones diarias (grupo "default")
  statement {
    sid    = "Programaciones"
    effect = "Allow"
    actions = [
      "scheduler:GetSchedule", "scheduler:CreateSchedule", "scheduler:UpdateSchedule",
      "scheduler:DeleteSchedule",
    ]
    resources = ["arn:aws:scheduler:${local.reg}:${local.acct}:schedule/default/${local.p}-*"]
  }

  # 11) CI/CD: leer (para el plan) y USAR la conexión y el proyecto, sin poder cambiarlos
  statement {
    sid       = "ConexionConGitHub"
    effect    = "Allow"
    actions   = local.connection_use_actions
    resources = local.connection_arns
  }
  statement {
    sid       = "LeerSuProyecto"
    effect    = "Allow"
    actions   = ["codebuild:BatchGetProjects"]
    resources = [local.deploy_project_arn]
  }

  # --- DENEGACIONES explícitas: un Deny gana siempre a cualquier Allow ---

  # Ni su propio rol ni el techo: solo puede LEERLOS (NotAction = "todo menos esto")
  statement {
    sid         = "NoTocarseASiMismoNiAlTecho"
    effect      = "Deny"
    not_actions = ["iam:Get*", "iam:List*"]
    resources   = [local.deployer_role_arn, local.boundary_arn]
  }
  # Nunca quitar un techo a ningún rol de la cuenta
  statement {
    sid       = "NoQuitarTechos"
    effect    = "Deny"
    actions   = ["iam:DeleteRolePermissionsBoundary"]
    resources = ["arn:aws:iam::${local.acct}:role/*"]
  }
  # Ni el proyecto de CodeBuild ni la conexión: quien controla el pipeline no puede ampliarlo
  statement {
    sid         = "NoTocarElPipeline"
    effect      = "Deny"
    not_actions = ["codebuild:BatchGetProjects", "codebuild:BatchGetBuilds"]
    resources   = [local.deploy_project_arn]
  }
  statement {
    sid         = "NoTocarLaConexion"
    effect      = "Deny"
    not_actions = local.connection_use_actions # solo leerla y usarla, con cualquiera de sus nombres
    resources   = local.connection_arns
  }
  # Ni cambiar el email de las alertas (silenciarlas) ni borrar los logs de sus propios despliegues
  statement {
    sid         = "NoSilenciarAlertas"
    effect      = "Deny"
    not_actions = ["ssm:GetParameter", "ssm:GetParameters", "ssm:ListTagsForResource"]
    resources   = ["arn:aws:ssm:${local.reg}:${local.acct}:parameter/${local.p}/alert_email"]
  }
  statement {
    sid    = "NoBorrarSusLogs"
    effect = "Deny"
    actions = [
      "logs:DeleteLogGroup", "logs:DeleteLogStream", "logs:PutRetentionPolicy",
      "logs:DeleteRetentionPolicy",
    ]
    resources = [
      "arn:aws:logs:${local.reg}:${local.acct}:log-group:/aws/codebuild/${local.deploy_project_name}",
      "arn:aws:logs:${local.reg}:${local.acct}:log-group:/aws/codebuild/${local.deploy_project_name}:*",
    ]
  }
  # Ni borrar los buckets (datos y state)
  statement {
    sid       = "NoBorrarBuckets"
    effect    = "Deny"
    actions   = ["s3:DeleteBucket"]
    resources = [var.bucket_arn, local.tfstate_bucket_arn]
  }
}

resource "aws_iam_role_policy" "deployer" {
  name   = "desplegar-marketpulse"
  role   = aws_iam_role.deployer.id
  policy = data.aws_iam_policy_document.deployer.json
}
