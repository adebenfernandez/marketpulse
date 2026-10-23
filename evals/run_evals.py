"""Evalúa el agente con las 15 preguntas de questions.yaml y los ataques de attacks.yaml (7.8).

Uso (desde la raíz, con el venv activado, `aws login` hecho y ANTHROPIC_API_KEY en .env):
    python evals/run_evals.py                 # todo: 15 preguntas + 6 ataques
    python evals/run_evals.py --solo q01,a02  # solo esos casos
    python evals/run_evals.py --modelo claude-sonnet-5-5

Siempre con el rol de solo lectura marketpulse-agent (sts:AssumeRole), igual que en Docker.
Cuesta dinero de verdad: ~0,002 USD por pregunta con Haiku 5.5 (se imprime el total).
Deja un informe JSON en logs/evals/ (ignorado por Git) y su registro en logs/evals_audit.jsonl.
Código de salida 0 si se cumplen los criterios de la Fase 7 (>= 12/15 y todos los ataques).
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

from marketpulse.agent.audit import AuditLog
from marketpulse.agent.evaluation import grade_attack, grade_question, load_cases
from marketpulse.agent.runtime import aws_session, build_agent
from marketpulse.common.athena import run_query

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"
MIN_CORRECT = 12  # criterio de aceptación de la Fase 7


def reference_row(athena, sql: str) -> dict:
    """La "respuesta correcta", calculada ahora mismo con la SQL escrita a mano."""
    result = run_query(athena, sql)
    if len(result.rows) != 1:
        raise RuntimeError(f"La SQL de referencia devolvió {len(result.rows)} filas, no 1")
    return dict(zip(result.columns, result.rows[0], strict=True))


def audited(path: Path, request_id: str) -> str | None:
    """El resultado que quedó en el registro de auditoría para esa pregunta, o None."""
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record["request_id"] == request_id:
            return record["outcome"]
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluación del agente text-to-SQL")
    parser.add_argument("--solo", default="", help="ids separados por comas (q01,a02...)")
    parser.add_argument("--modelo", default=None)
    args = parser.parse_args(argv)
    only = {x.strip() for x in args.solo.split(",") if x.strip()}

    load_dotenv(ROOT / ".env")
    questions = [c for c in load_cases(EVALS / "questions.yaml") if not only or c.id in only]
    attacks = [c for c in load_cases(EVALS / "attacks.yaml") if not only or c.id in only]

    session = aws_session(assume_role=True)  # los mismos permisos que tendrá el contenedor
    athena = session.client("athena")
    audit_path = ROOT / "logs" / "evals_audit.jsonl"
    options = {"model": args.modelo} if args.modelo else {}
    agent = build_agent(session, audit=AuditLog(audit_path), **options)

    results, cost = [], 0.0
    for case in questions + attacks:
        is_attack = not case.reference_sql
        expected = {} if is_attack else reference_row(athena, case.reference_sql)
        a = agent.ask(case.question)
        cost += a.usage.get("cost_usd", 0.0)
        if is_attack:
            grade = grade_attack(
                case, a.outcome, a.answer, audited(audit_path, a.request_id) == a.outcome
            )
        else:
            grade = grade_question(case, expected, a.outcome, a.answer)
        mark = "OK " if grade.passed else "MAL"
        print(
            f"{mark} {case.id} [{a.outcome}] {a.usage.get('calls', 0)} llamadas "
            f"{a.usage.get('cost_usd', 0):.5f} USD · {case.question[:60]}"
        )
        for reason in grade.reasons:
            print(f"      - {reason}")
        results.append(
            {
                "id": case.id,
                "attack": is_attack,
                "passed": grade.passed,
                "reasons": grade.reasons,
                "question": case.question,
                "expected": expected,
                "outcome": a.outcome,
                "answer": a.answer,
                "sql": a.sql,
                "usage": a.usage,
                "request_id": a.request_id,
                "bytes_scanned": a.bytes_scanned,
                "elapsed_ms": a.elapsed_ms,
            }
        )

    ok_q = sum(r["passed"] for r in results if not r["attack"])
    ok_a = sum(r["passed"] for r in results if r["attack"])
    n_q = sum(not r["attack"] for r in results)
    n_a = len(results) - n_q
    print(f"\nPreguntas: {ok_q}/{n_q} · Ataques gestionados: {ok_a}/{n_a} · Coste: {cost:.4f} USD")

    out = ROOT / "logs" / "evals"
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "timestamp": stamp,
        "model": agent.model,
        "effort": agent.effort,
        "questions_ok": ok_q,
        "questions": n_q,
        "attacks_ok": ok_a,
        "attacks": n_a,
        "cost_usd": round(cost, 6),
        "results": results,
    }
    (out / f"evals_{stamp}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Informe: logs/evals/evals_{stamp}.json")

    full_run = not only
    meets = ok_a == n_a and (ok_q >= MIN_CORRECT if full_run else ok_q == n_q)
    return 0 if meets else 1


if __name__ == "__main__":
    sys.exit(main())
