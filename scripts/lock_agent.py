"""Genera config/agent-requirements.txt: lo que instala la imagen Docker del agente (paso 7.9).

Uso (desde la raíz, con el venv activado): python scripts/lock_agent.py

Mismo método que el bloqueo de la Lambda (scripts/build_lambda.py, D-027): las dependencias que
necesita el agente y las de estas, con la versión EXACTA instalada en el venv local, que es la que
ha pasado los tests. Así la imagen no instala "lo último que haya hoy en PyPI".

El agente no necesita pandas ni pyarrow (son de la transformación): la imagen copia el código de
marketpulse (PYTHONPATH) y solo instala estas dependencias.
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "config" / "agent-requirements.txt"

# Lo que importan api/main.py y marketpulse.agent (sin evaluation.py, que es solo para evals/)
AGENT_RUNTIME = ["anthropic", "boto3", "fastapi", "sqlglot", "uvicorn"]

_spec = importlib.util.spec_from_file_location("build_lambda", ROOT / "scripts" / "build_lambda.py")
build_lambda = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_lambda)


def write_agent_lock(path: Path = LOCK_PATH) -> dict[str, str]:
    pins = build_lambda.pinned_closure(AGENT_RUNTIME)
    header = (
        "# Dependencias de la imagen Docker del agente, con versión EXACTA (api/Dockerfile).\n"
        "# Se generan desde el venv local: python scripts/lock_agent.py\n"
    )
    lines = [f"{name}=={version}" for name, version in sorted(pins.items())]
    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return pins


if __name__ == "__main__":
    pins = write_agent_lock()
    print(f"{LOCK_PATH.relative_to(ROOT)}: {len(pins)} paquetes")
    sys.exit(0)
