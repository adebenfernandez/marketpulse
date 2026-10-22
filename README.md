# MarketPulse

Plataforma de datos de mercados en AWS (Lambda, S3, Athena) con agente text-to-SQL.

> En construcción. El README completo se escribirá en la Fase 8.

## Desplegar desde cero

Toda la infraestructura está en Terraform (`infra/`). Nada se crea a mano en la consola: lo único
que se hace fuera de Terraform son los **secretos** (las claves de API y tu email), que nunca pasan
por el código.

Los comandos son de **PowerShell** (Windows). Se ejecutan desde la raíz del repositorio salvo que
se indique otra carpeta.

### 0. Requisitos

- Una cuenta de AWS con acceso a la región **`eu-north-1`** y la **AWS CLI v2** con un perfil
  (aquí, `marketpulse`, con `aws login --profile marketpulse`). Credenciales temporales, nunca
  claves de acceso permanentes.
- **Terraform ≥ 1.10** (probado con 1.16.6): el bloqueo del *state* usa `use_lockfile`.
- **Python 3.13**.
- Claves gratuitas de [CoinGecko](https://www.coingecko.com/en/api) (plan Demo) y
  [Alpha Vantage](https://www.alphavantage.co/support/#api-key).

### 1. Entorno de Python

```powershell
python -m venv C:\Users\<tú>\.venvs\marketpulse        # fuera de OneDrive o Dropbox, si lo usas
& C:\Users\<tú>\.venvs\marketpulse\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env       # rellena tus claves de API (el bucket, después del paso 6)
```

**Deja el venv activado** en la terminal donde ejecutes Terraform. El despliegue de las vistas de
Athena (`terraform_data` en `infra/modules/analytics/views.tf`) lanza
`python -m marketpulse.common.athena`. Sin el venv falla con
`ModuleNotFoundError: No module named 'marketpulse'`. No rompe nada: el recurso queda *tainted* y
el siguiente `apply` lo repite.

### 2. Credenciales y variables de entorno

```powershell
aws login --profile marketpulse                     # sesión temporal (12 h)
$env:AWS_PROFILE = "marketpulse"
# Opcional: guardar la carpeta .terraform fuera de la sincronización en la nube. Es una carpeta
# DISTINTA para bootstrap y para infra, y debe ser la misma en todos los comandos de cada una.
$env:TF_DATA_DIR = "C:\Users\<tú>\.terraform-data\marketpulse-bootstrap"
```

### 3. Bucket del *state* (`infra/bootstrap/`, solo la primera vez)

El *state* de `infra/` vive en un bucket de S3 que tiene que existir antes. Lo crea esta
configuración pequeña, que guarda su propio *state* en local (D-025).

```powershell
cd infra\bootstrap
terraform init
terraform plan -out=tfplan        # esperado: 7 to add, 0 to change, 0 to destroy
terraform apply tfplan
terraform output tfstate_bucket_name
cd ..\..
```

### 4. Configuración de este despliegue (ficheros ignorados por Git)

```powershell
Copy-Item infra\backend.hcl.example infra\backend.hcl              # pon el bucket del paso 3
Copy-Item infra\terraform.tfvars.example infra\terraform.tfvars    # tu email de alertas y el bucket del paso 3
```

### 5. Paquete de las Lambdas

```powershell
python scripts/build_lambda.py    # genera build/lambda.zip (arm64, determinista)
```

### 6. Toda la infraestructura (`infra/`)

```powershell
$env:TF_DATA_DIR = "C:\Users\<tú>\.terraform-data\marketpulse"   # si usas TF_DATA_DIR
cd infra
terraform init -backend-config="backend.hcl"
terraform plan -out=tfplan        # revisa el plan: solo debe haber "to add"
terraform apply tfplan
cd ..
```

Se crean los cinco módulos:
- `storage`: el data lake en S3.
- `compute`: las Lambdas, IAM, SSM, los logs y la programación diaria.
- `analytics`: Glue, Athena y las vistas.
- `monitoring`: SNS, el presupuesto de 5 USD con alertas al 50/80/100 % y las alarmas.
- `cicd`: la conexión con GitHub, el techo de permisos (*boundary*), el rol de despliegue y el
  proyecto de CodeBuild con su *webhook* (D-027, D-028).

**La primera vez, este `apply` falla en el proyecto de CodeBuild** (`User is not authorized to
access connection`): la conexión con GitHub nace en `PENDING` y no se puede usar hasta autorizarla.
Haz el paso 7.4 y repite `terraform plan -out=tfplan` y `terraform apply tfplan`. Si usas un *fork*,
cambia antes `github_repository_url` en `infra/main.tf`.

### 7. Pasos que no hace Terraform (a propósito)

1. **Confirmar el email de alertas.** SNS envía un correo de confirmación a la dirección de
   `terraform.tfvars`. Hasta que pulses el enlace no llegará ninguna alerta (ni del presupuesto,
   ni de las alarmas, ni de los fallos de las Lambdas).
2. **Escribir las claves de API en SSM.** Terraform crea los parámetros con un valor de relleno
   (D-021). Cópialas desde tu `.env` sin que queden en el historial de PowerShell:

   ```powershell
   $k = ((Select-String -Path .env -Pattern '^COINGECKO_API_KEY=').Line -split '=', 2)[1].Trim()
   aws ssm put-parameter --name /marketpulse/coingecko_api_key --type SecureString --value $k --overwrite
   $k = ((Select-String -Path .env -Pattern '^ALPHAVANTAGE_API_KEY=').Line -split '=', 2)[1].Trim()
   aws ssm put-parameter --name /marketpulse/alphavantage_api_key --type SecureString --value $k --overwrite
   Remove-Variable k
   ```

   Hasta que lo hagas, la ingesta programada (06:00 UTC) fallará y te avisará por email.

3. **Apuntar el código local al bucket nuevo.** En `.env`, pon en `MARKETPULSE_BUCKET` el valor de
   `terraform -chdir=infra output -raw datalake_bucket_name` (lo usan la carga histórica y la
   subida manual a S3).
4. **Autorizar la conexión con GitHub.** En la consola de AWS → *Developer Tools* → *Connections*
   (región `eu-north-1`) → `marketpulse-github` → *Update pending connection*. Autoriza e instala
   la app *AWS Connector for GitHub* con **"Only select repositories"** → este repositorio. El
   estado pasa a `AVAILABLE` (`terraform output github_connection_status`).

### 8. Primera ejecución y comprobación

```powershell
aws lambda invoke --function-name marketpulse-ingest --cli-read-timeout 600 "$env:TEMP\out.json"      # ingesta
aws lambda invoke --function-name marketpulse-transform --cli-read-timeout 600 "$env:TEMP\out.json"   # silver y gold
python -m marketpulse.ingest.backfill    # opcional: un año de historia de cripto y divisas (D-022)
cd infra; terraform plan; cd ..          # esperado: "No changes"
```

A partir de aquí, EventBridge Scheduler ejecuta la ingesta a las 06:00 UTC y la transformación a
las 06:30 UTC todos los días.

## Despliegue continuo (después del primer despliegue)

Ya no se despliega desde el portátil. El flujo normal es:

1. Rama → *pull request* hacia `main` → **GitHub Actions** (`.github/workflows/ci.yml`) ejecuta
   ruff, pytest y `terraform fmt`/`validate`, sin credenciales de AWS.
2. *Merge* a `main` → el *webhook* lanza **CodeBuild** (`buildspec.yml`) con el rol
   `marketpulse-deployer`: repite ruff y pytest, construye el zip, hace `terraform plan`, pasa la
   **guardia** (`scripts/check_plan.py`, que para si algo se borra o se reemplaza) y aplica.
   Logs: `/aws/codebuild/marketpulse-deploy` (14 días).

Excepciones, a propósito:
- **Cambios en `infra/modules/cicd/`** (el rol de despliegue, el techo, CodeBuild o la conexión):
  el *deployer* tiene prohibido tocarlos, así que se aplican **a mano** antes de fusionar.
- **Si la guardia para el despliegue**, revisa el *plan* y, si el borrado es intencionado,
  aplícalo a mano.
- **Si cambias las dependencias** en `pyproject.toml`, regenera el bloqueo de la Lambda con
  `python scripts/build_lambda.py --update-lock` (un test lo exige).

## Desmontar

`terraform destroy` en `infra/` borra todo menos el bucket del data lake si tiene datos
(`force_destroy = false`): primero hay que vaciarlo. El bucket del *state* (`infra/bootstrap/`) va
el último: tiene `prevent_destroy`, así que hay que quitar esa línea antes de su `terraform destroy`,
y vaciar sus versiones (el versionado las conserva).
