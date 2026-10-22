output "github_connection_arn" {
  description = "ARN de la conexión con GitHub (la usará el proyecto de CodeBuild)"
  value       = aws_codeconnections_connection.github.arn
}

output "github_connection_status" {
  description = "PENDING hasta que se autoriza en la consola; después, AVAILABLE"
  value       = aws_codeconnections_connection.github.connection_status
}

output "workload_boundary_arn" {
  description = "ARN del permissions boundary que deben llevar los roles de compute"
  value       = aws_iam_policy.workload_boundary.arn
}
