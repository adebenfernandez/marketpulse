output "alertas_topic_arn" {
  description = "ARN del tema SNS de alertas (construido: se conoce antes del apply)"
  value       = local.alertas_topic_arn
}
