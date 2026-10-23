"""CLI del agente: python -m marketpulse.agent "¿Qué activo ha sido más volátil este mes?"

En local, con `aws login` y AWS_PROFILE=marketpulse, añade --rol para usar los permisos de solo
lectura del rol marketpulse-agent (recomendado: así se prueba lo mismo que en Docker).
"""

import argparse
import logging
import sys

from dotenv import load_dotenv

from marketpulse.agent.runtime import MissingApiKeyError, aws_session, build_agent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pregunta al agente text-to-SQL de MarketPulse")
    parser.add_argument("question", help="La pregunta, en español")
    parser.add_argument("--rol", action="store_true", help="Asumir el rol marketpulse-agent")
    parser.add_argument("--modelo", default=None, help="Modelo de Claude (por defecto, Haiku 5.5)")
    parser.add_argument("--effort", default=None, choices=["low", "medium", "high"])
    args = parser.parse_args(argv)

    load_dotenv()  # ANTHROPIC_API_KEY desde .env (ignorado por Git)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    options = {k: v for k, v in {"model": args.modelo, "effort": args.effort}.items() if v}
    try:
        agent = build_agent(aws_session(assume_role=args.rol), **options)
    except MissingApiKeyError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    a = agent.ask(args.question)
    print(f"\n[{a.outcome}] {a.answer}\n")
    if a.sql:
        print(f"SQL:\n{a.sql}\n\nExplicación: {a.explanation}\n")
    u = a.usage
    print(
        f"{u['calls']} llamadas · {u['input_tokens']} tokens de entrada "
        f"(+{u['cache_read_tokens']} de caché) · {u['output_tokens']} de salida · "
        f"{u['cost_usd']:.5f} USD · {a.bytes_scanned} bytes leídos en Athena · "
        f"{a.elapsed_ms / 1000:.1f} s · id {a.request_id}"
    )
    return 1 if a.outcome == "error" else 0


if __name__ == "__main__":
    sys.exit(main())
