variable "project" {
  description = "Nombre del proyecto: nombre de la base de datos de Glue y del workgroup"
  type        = string
}

variable "bucket_name" {
  description = "Bucket del data lake (ubicación de las tablas y de los resultados de Athena)"
  type        = string
}

variable "athena_results_prefix" {
  description = "Prefijo de los resultados de Athena dentro del bucket"
  type        = string
}

variable "project_root" {
  description = "Raíz del proyecto: ahí están sql/views y ahí se ejecuta el despliegue de vistas"
  type        = string
}
