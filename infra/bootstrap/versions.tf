# Configuración "bootstrap" (arranque): crea SOLO el bucket donde vivirá el state del resto de
# infra/. Es el problema del huevo y la gallina: el backend remoto necesita un bucket que ya
# exista, así que este bucket no puede guardarse en sí mismo. Por eso esta configuración es
# independiente, muy pequeña y con state LOCAL (infra/bootstrap/terraform.tfstate, ignorado por
# Git). Si ese fichero se perdiera, el bucket se recupera con un import: no guarda nada valioso.
terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.69" # las mismas restricciones que infra/ (el lock file fija 6.69.1)
    }
  }
}
