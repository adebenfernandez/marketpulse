# Bloques moved: le dicen a Terraform "este recurso NO es nuevo: es el mismo que antes estaba en
# esta otra dirección". Sin ellos, al pasar los recursos a módulos, el plan propondría DESTRUIR
# cada recurso en su dirección vieja y CREARLO en la nueva (perderíamos el bucket, las Lambdas...).
# Con ellos, Terraform solo cambia la dirección dentro del state: en AWS no se toca nada.
#
# Para un recurso con for_each, mover el recurso sin clave mueve TODAS sus instancias.
# Una vez aplicados ya no hacen nada; se conservan como historial del refactor (recomendación de
# la documentación de Terraform) y porque en un despliegue desde cero no molestan.

# --- storage ---
moved {
  from = aws_s3_bucket.datalake
  to   = module.storage.aws_s3_bucket.datalake
}
moved {
  from = aws_s3_bucket_public_access_block.datalake
  to   = module.storage.aws_s3_bucket_public_access_block.datalake
}
moved {
  from = aws_s3_bucket_server_side_encryption_configuration.datalake
  to   = module.storage.aws_s3_bucket_server_side_encryption_configuration.datalake
}
moved {
  from = aws_s3_bucket_ownership_controls.datalake
  to   = module.storage.aws_s3_bucket_ownership_controls.datalake
}
moved {
  from = aws_s3_bucket_policy.datalake
  to   = module.storage.aws_s3_bucket_policy.datalake
}
moved {
  from = aws_s3_bucket_lifecycle_configuration.datalake
  to   = module.storage.aws_s3_bucket_lifecycle_configuration.datalake
}

# --- compute ---
moved {
  from = aws_ssm_parameter.api_keys
  to   = module.compute.aws_ssm_parameter.api_keys
}
moved {
  from = aws_cloudwatch_log_group.lambda
  to   = module.compute.aws_cloudwatch_log_group.lambda
}
moved {
  from = aws_iam_role.lambda
  to   = module.compute.aws_iam_role.lambda
}
moved {
  from = aws_iam_role_policy.ingest
  to   = module.compute.aws_iam_role_policy.ingest
}
moved {
  from = aws_iam_role_policy.transform
  to   = module.compute.aws_iam_role_policy.transform
}
moved {
  from = aws_lambda_function.this
  to   = module.compute.aws_lambda_function.this
}
moved {
  from = aws_lambda_function_event_invoke_config.this
  to   = module.compute.aws_lambda_function_event_invoke_config.this
}
moved {
  from = aws_iam_role.scheduler
  to   = module.compute.aws_iam_role.scheduler
}
moved {
  from = aws_iam_role_policy.scheduler
  to   = module.compute.aws_iam_role_policy.scheduler
}
moved {
  from = aws_scheduler_schedule.daily
  to   = module.compute.aws_scheduler_schedule.daily
}

# --- analytics ---
moved {
  from = aws_glue_catalog_database.marketpulse
  to   = module.analytics.aws_glue_catalog_database.marketpulse
}
moved {
  from = aws_glue_catalog_table.daily_prices
  to   = module.analytics.aws_glue_catalog_table.daily_prices
}
moved {
  from = aws_glue_catalog_table.dim_asset
  to   = module.analytics.aws_glue_catalog_table.dim_asset
}
moved {
  from = aws_athena_workgroup.marketpulse
  to   = module.analytics.aws_athena_workgroup.marketpulse
}
moved {
  from = terraform_data.athena_views
  to   = module.analytics.terraform_data.athena_views
}

# --- monitoring ---
moved {
  from = aws_sns_topic.alertas
  to   = module.monitoring.aws_sns_topic.alertas
}
moved {
  from = aws_sns_topic_policy.alertas
  to   = module.monitoring.aws_sns_topic_policy.alertas
}
moved {
  from = aws_sns_topic_subscription.email
  to   = module.monitoring.aws_sns_topic_subscription.email
}
moved {
  from = aws_budgets_budget.mensual
  to   = module.monitoring.aws_budgets_budget.mensual
}
moved {
  from = aws_cloudwatch_metric_alarm.lambda_errors
  to   = module.monitoring.aws_cloudwatch_metric_alarm.lambda_errors
}
