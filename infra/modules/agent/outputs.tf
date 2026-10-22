output "agent_role_arn" {
  description = "Rol de solo lectura que se pone el contenedor del agente (sts:AssumeRole, 1 h)"
  value       = aws_iam_role.agent.arn
}
