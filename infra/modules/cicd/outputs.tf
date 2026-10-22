output "github_connection_arn" {
  description = "ARN de la conexión con GitHub (la usará el proyecto de CodeBuild)"
  value       = aws_codeconnections_connection.github.arn
}

output "github_connection_status" {
  description = "PENDING hasta que se autoriza en la consola; después, AVAILABLE"
  value       = aws_codeconnections_connection.github.connection_status
}
