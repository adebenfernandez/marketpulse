# Vistas de Athena (sql/views/*.sql), desplegadas desde Terraform.
#
# El proveedor de AWS no tiene un recurso para "vista de Athena". terraform_data (incluido en
# Terraform, sin proveedor nuevo) ejecuta un comando local que lanza cada CREATE OR REPLACE VIEW
# con nuestro módulo de Python. Solo se vuelve a ejecutar cuando cambia algo de lo que hay en
# triggers_replace. REQUISITO: ejecutar terraform con el venv activado (usa `python`).

locals {
  views_dir  = "${path.module}/../sql/views"
  view_files = sort(fileset(local.views_dir, "*.sql"))
}

resource "terraform_data" "athena_views" {
  # Si cambia cualquier .sql (su huella), o se recrean las tablas o el workgroup, se redespliega
  triggers_replace = {
    sql       = sha256(join(",", [for f in local.view_files : "${f}:${filesha256("${local.views_dir}/${f}")}"]))
    tables    = join(",", [aws_glue_catalog_table.daily_prices.id, aws_glue_catalog_table.dim_asset.id])
    workgroup = aws_athena_workgroup.marketpulse.id
  }

  provisioner "local-exec" {
    command     = "python -m marketpulse.common.athena --deploy-views sql/views"
    working_dir = "${path.module}/.." # la raíz del proyecto
  }
}
