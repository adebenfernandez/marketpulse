# Arranca el contenedor del agente con credenciales TEMPORALES de solo lectura (paso 7.9, D-037).
#
# Uso (PowerShell, desde la raíz del proyecto, después de `aws login --profile marketpulse` y de
# construir la imagen con `docker build -f api/Dockerfile -t marketpulse-agent:local .`):
#     .\scripts\run_agent_docker.ps1
# La API queda en http://127.0.0.1:8000 (solo este ordenador). Ctrl+C la para.
#
# Qué hace, sin escribir ningún secreto en disco ni en pantalla:
#   1. Lee ANTHROPIC_API_KEY de .env.
#   2. Con tu sesión de `aws login` se pone el rol marketpulse-agent (sts:AssumeRole): recibe
#      credenciales que caducan en 1 hora (encadenamiento de roles) y solo pueden LEER.
#   3. Las pone como variables de entorno DE ESTE PROCESO y lanza `docker run -e NOMBRE`: con -e
#      sin "=valor", Docker copia el valor del proceso; no aparece en la línea de comandos.
#   4. Al terminar, borra esas variables del proceso.
# Cuando caduquen (1 h), las preguntas acabarán en "error": vuelve a ejecutar el script.

param(
    [string]$AwsProfile = "marketpulse",
    [string]$Image = "marketpulse-agent:local",
    [int]$Port = 8000
)
$ErrorActionPreference = "Stop"
$names = "ANTHROPIC_API_KEY", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"

try {
    # 1. Clave de Anthropic desde .env (la primera línea ANTHROPIC_API_KEY=...)
    $line = Get-Content .env | Where-Object { $_ -match '^\s*ANTHROPIC_API_KEY\s*=' } | Select-Object -First 1
    if (-not $line) { throw "No hay ANTHROPIC_API_KEY en .env" }
    $env:ANTHROPIC_API_KEY = ($line -split '=', 2)[1].Trim().Trim('"').Trim("'")

    # 2. Credenciales temporales del rol de solo lectura
    $account = aws sts get-caller-identity --profile $AwsProfile --query Account --output text
    if ($LASTEXITCODE -ne 0) { throw "Sin sesión de AWS: ejecuta 'aws login --profile $AwsProfile'" }
    $roleArn = "arn:aws:iam::${account}:role/marketpulse-agent"
    $creds = aws sts assume-role --profile $AwsProfile --role-arn $roleArn `
        --role-session-name marketpulse-docker --query Credentials --output json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw "No se pudo asumir el rol marketpulse-agent" }

    # 3. Variables del proceso (no se muestran) y contenedor
    $env:AWS_ACCESS_KEY_ID = $creds.AccessKeyId
    $env:AWS_SECRET_ACCESS_KEY = $creds.SecretAccessKey
    $env:AWS_SESSION_TOKEN = $creds.SessionToken
    Write-Host "Rol marketpulse-agent asumido; las credenciales caducan: $($creds.Expiration)"
    Write-Host "API en http://127.0.0.1:$Port  (Ctrl+C para parar)"

    docker run --rm --name marketpulse-agent `
        -p "127.0.0.1:${Port}:8000" `
        -e ANTHROPIC_API_KEY -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN `
        $Image
}
finally {
    # 4. Nada se queda en el proceso de PowerShell
    foreach ($n in $names) { Remove-Item "Env:$n" -ErrorAction SilentlyContinue }
}
