output "athena_workgroup" {
  description = "Workgroup de Athena para todas las consultas de MarketPulse"
  value       = aws_athena_workgroup.marketpulse.name
}
