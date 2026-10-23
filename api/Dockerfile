# Imagen del agente text-to-SQL de MarketPulse (paso 7.9, D-037).
#
# Construir (desde la RAÍZ del proyecto: el contexto necesita src/, api/ y config/):
#     docker build -f api/Dockerfile -t marketpulse-agent:local .
# Ejecutar: scripts/run_agent_docker.ps1 (pone las credenciales temporales y la clave sin
# escribirlas en disco). NUNCA se copian .env ni credenciales dentro de la imagen (.dockerignore).

# Python 3.13.15, la misma versión que el venv local y las Lambdas, fijada por su huella (digest):
# la etiqueta "3.13.15-slim" podría moverse a otra imagen; el digest no (como las acciones de
# GitHub fijadas por SHA, paso 6.3). Imagen "slim": Debian mínimo, sin compiladores
FROM python:3.13.15-slim@sha256:7c61056e61ac89e852de05f3dc6fa51a6dd2181797bceed46aa725dd7cb2cd3b

# Sin .pyc en disco y salida sin búfer: los logs (y el registro de auditoría) salen al momento
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AWS_DEFAULT_REGION=eu-north-1 \
    MARKETPULSE_AUDIT_LOG=/app/logs/agent_audit.jsonl

WORKDIR /app

# 1) Dependencias primero, en su propia capa: si solo cambia el código, Docker reutiliza esta
#    capa (la más lenta) de la construcción anterior
COPY config/agent-requirements.txt config/agent-requirements.txt
RUN pip install --requirement config/agent-requirements.txt

# 2) Nuestro código, sin instalarlo como paquete: basta con que Python lo encuentre (PYTHONPATH).
#    Así no se cuelan pandas ni pyarrow (dependencias de pyproject que el agente no usa) y la
#    construcción no descarga setuptools sin versión fija
ENV PYTHONPATH=/app/src:/app
COPY src/marketpulse/ src/marketpulse/
COPY api/ api/

# 3) Usuario sin privilegios: si alguien tomara el control del proceso, no sería root en el
#    contenedor. Solo puede escribir en logs/
RUN useradd --create-home --uid 10001 agente && mkdir -p /app/logs && chown agente /app/logs
USER agente

EXPOSE 8000
# 0.0.0.0 DENTRO del contenedor (si no, no se ve desde fuera); quién puede llegar desde fuera lo
# decide `docker run -p 127.0.0.1:8000:8000` (solo este ordenador)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
