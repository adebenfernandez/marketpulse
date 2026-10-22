# Las dos funciones Lambda. Las dos usan el MISMO zip (build/lambda.zip, generado con
# `python scripts/build_lambda.py`) y cambian el handler, la memoria y la configuración.

locals {
  lambda_zip = var.lambda_zip_path

  # Capa gestionada AWS SDK for pandas 3.17.1 para Python 3.13 en arm64 (paso 3.1, D-020)
  pandas_layer_arn = "arn:aws:lambda:${local.region}:336392948345:layer:AWSSDKPandas-Python313-Arm64:16"

  lambda_settings = {
    ingest = {
      handler     = "marketpulse.ingest.handler.handler"
      description = "Ingesta diaria: Frankfurter, CoinGecko y Alpha Vantage -> bronze"
      memory_mb   = 256 # solo HTTP y JSON: no carga pandas
      # Peor caso: 5 peticiones con hasta 4 intentos de 10 s más esperas exponenciales
      timeout_s = 300
      layers    = [] # la ingesta no importa pandas: sin capa, el arranque en frío es más rápido
      environment = {
        COINGECKO_API_KEY_PARAM    = aws_ssm_parameter.api_keys["coingecko_api_key"].name
        ALPHAVANTAGE_API_KEY_PARAM = aws_ssm_parameter.api_keys["alphavantage_api_key"].name
      }
    }
    transform = {
      handler     = "marketpulse.transform.handler.handler"
      description = "Transformacion diaria: bronze -> silver y gold, con calidad de datos"
      memory_mb   = 1024 # pandas y pyarrow en memoria; en Lambda, más memoria = más CPU
      timeout_s   = 120
      layers      = [local.pandas_layer_arn]
      environment = {}
    }
  }
}

resource "aws_lambda_function" "this" {
  for_each = local.lambda_settings

  function_name = local.lambda_functions[each.key] # marketpulse-ingest, marketpulse-transform
  description   = each.value.description
  role          = aws_iam_role.lambda[each.key].arn # su rol de ejecución (paso 3.6)

  runtime       = "python3.13"
  architectures = ["arm64"] # Graviton: un 20 % más barato (D-020)
  handler       = each.value.handler
  memory_size   = each.value.memory_mb
  timeout       = each.value.timeout_s
  layers        = each.value.layers

  filename = local.lambda_zip
  # Huella del zip: si cambia (código o dependencias), Terraform sube la versión nueva.
  # Como el zip es determinista, si nada ha cambiado la huella tampoco, y no se redespliega
  source_code_hash = filebase64sha256(local.lambda_zip)

  environment {
    variables = merge(
      {
        MARKETPULSE_BUCKET = var.bucket_name # nombre del bucket (no es secreto)
        LOG_LEVEL          = "INFO"
      },
      each.value.environment, # solo NOMBRES de parámetros de SSM, nunca los valores
    )
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.lambda[each.key].name # el grupo con retención de 14 días
  }

  # Que los permisos existan antes de que la función pueda ejecutarse por primera vez
  depends_on = [aws_iam_role_policy.ingest, aws_iam_role_policy.transform]
}

# --- Invocación asíncrona (la que usa EventBridge Scheduler): reintentos y destino de fallo ---

resource "aws_lambda_function_event_invoke_config" "this" {
  for_each = aws_lambda_function.this

  function_name = each.value.function_name

  # Si la función lanza una excepción, Lambda la reintenta 2 veces (al cabo de ~1 y ~2 minutos).
  # Es seguro: la ingesta es idempotente y la transformación reconstruye todo desde bronze
  maximum_retry_attempts       = 2
  maximum_event_age_in_seconds = 3600

  # Si fallan los 3 intentos, Lambda envía el evento y el error al tema SNS (y de ahí, al email).
  # Hace el papel de la "dead-letter queue" sin necesitar SQS
  destination_config {
    on_failure {
      destination = var.alertas_topic_arn
    }
  }

  # El rol necesita sns:Publish ANTES de que haga falta enviar el primer fallo
  depends_on = [aws_iam_role_policy.ingest, aws_iam_role_policy.transform]
}
