# Módulo raíz de MarketPulse: solo conecta los módulos de infra/modules/.
#
#   storage    -> bucket del data lake (bronze/silver/gold) y sus protecciones
#   compute    -> Lambdas, sus roles de IAM, logs, claves en SSM y programación diaria
#   analytics  -> Glue Data Catalog, workgroup de Athena y vistas SQL
#   monitoring -> tema SNS de alertas, presupuesto y alarmas de CloudWatch
#   cicd       -> despliegue continuo: conexión con GitHub y CodeBuild (Fase 6, D-027)
#
# Cada módulo recibe lo que necesita por variables y devuelve lo que otros usan por outputs.
# Los recursos se trajeron aquí desde los ficheros sueltos de infra/ con bloques moved (moved.tf).

# Datos de la cuenta y la región actuales, para construir ARN sin escribir el número de cuenta en
# el código (el repositorio será público). Se leen una vez y se pasan a los módulos
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.region
}

module "storage" {
  source  = "./modules/storage"
  project = var.project
}

module "monitoring" {
  source      = "./modules/monitoring"
  project     = var.project
  account_id  = local.account_id
  region      = local.region
  alert_email = var.alert_email

  # Las alarmas vigilan las funciones de compute (nombres fijos, conocidos antes del apply)
  lambda_function_names = module.compute.lambda_function_names
}

module "compute" {
  source     = "./modules/compute"
  project    = var.project
  account_id = local.account_id
  region     = local.region

  bucket_name       = module.storage.bucket_name
  bucket_arn        = module.storage.bucket_arn
  alertas_topic_arn = module.monitoring.alertas_topic_arn
  lambda_zip_path   = "${path.root}/../build/lambda.zip" # generado con scripts/build_lambda.py

  permissions_boundary_arn = module.cicd.workload_boundary_arn # techo de sus roles (D-028)
}

module "analytics" {
  source  = "./modules/analytics"
  project = var.project

  bucket_name           = module.storage.bucket_name
  athena_results_prefix = module.storage.athena_results_prefix
  project_root          = "${path.root}/.." # sql/views y el comando de despliegue de vistas
}

module "cicd" {
  source     = "./modules/cicd"
  project    = var.project
  account_id = local.account_id
  region     = local.region

  bucket_arn        = module.storage.bucket_arn
  alertas_topic_arn = module.monitoring.alertas_topic_arn
}
