"""Montar el agente con credenciales reales: lo comparten la CLI (7.7) y la API (7.9).

Credenciales de AWS (D-033), nunca claves permanentes:
- En Docker llegan como variables de entorno con las credenciales TEMPORALES del rol
  marketpulse-agent (las crea scripts/... en el paso 7.9): boto3 las lee solas.
- En local, con `aws login` (AWS_PROFILE=marketpulse) tienes el rol de administración. Con
  assume_role=True se pone antes el rol de solo lectura, para probar con los permisos reales.
La clave de la API de Claude se lee de ANTHROPIC_API_KEY (en .env o en el entorno del contenedor).
"""

import os

import anthropic
import boto3

from marketpulse.agent.agent import DEFAULT_MODEL, Agent
from marketpulse.agent.audit import AuditLog, default_audit_log
from marketpulse.agent.tools import AgentTools

AGENT_ROLE_NAME = "marketpulse-agent"


class MissingApiKeyError(RuntimeError):
    """Sin ANTHROPIC_API_KEY no se puede llamar al modelo (y no se busca en otros sitios)."""


def aws_session(assume_role: bool = False) -> boto3.Session:
    base = boto3.Session()  # variables de entorno, o el perfil de AWS_PROFILE
    if not assume_role:
        return base
    sts = base.client("sts")
    role_arn = os.environ.get("MARKETPULSE_AGENT_ROLE_ARN") or (
        f"arn:aws:iam::{sts.get_caller_identity()['Account']}:role/{AGENT_ROLE_NAME}"
    )
    creds = sts.assume_role(RoleArn=role_arn, RoleSessionName="marketpulse-agent-local")[
        "Credentials"
    ]  # 1 h como máximo: encadenamiento de roles
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=base.region_name,
    )


def build_agent(
    session: boto3.Session, model: str = DEFAULT_MODEL, audit: AuditLog | None = None, **kwargs
) -> Agent:
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        raise MissingApiKeyError("Falta ANTHROPIC_API_KEY (en .env o en el entorno)")
    glue, athena = session.client("glue"), session.client("athena")  # clientes compartidos
    return Agent(
        client=anthropic.Anthropic(),  # lee ANTHROPIC_API_KEY; reintenta 429 y 5xx (2 veces)
        tools_factory=lambda: AgentTools(glue, athena),
        audit=audit or default_audit_log(),
        model=model,
        **kwargs,
    )
