# El nombre del bucket hace falta en el paso siguiente para configurar el backend de infra/
output "tfstate_bucket_name" {
  description = "Nombre del bucket del state de Terraform"
  value       = aws_s3_bucket.tfstate.bucket
}
