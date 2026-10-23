"""Tests de la corrección de las evaluaciones (paso 7.8, D-036) y de los ficheros de evals/."""

from pathlib import Path

import pytest

from marketpulse.agent.evaluation import (
    Case,
    Check,
    extract_numbers,
    grade_attack,
    grade_question,
    load_cases,
    number_matches,
    text_matches,
)
from marketpulse.agent.guard import validate_sql

EVALS = Path(__file__).resolve().parents[1] / "evals"


# --- Leer cifras escritas en español (o en inglés) ---


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("subió un +6,39 %", 6.39),
        ("cerró en 78.552,78 USD", 78552.78),
        ("EUR/USD llegó a 1,1745", 1.1745),
        ("correlación de 0.85", 0.85),
        ("bajó un -2 %", 2.0),
        ("21 sesiones.", 21.0),
        ("−3,5 %", 3.5),  # signo menos tipográfico
    ],
)
def test_extract_numbers(text, value):
    assert value in extract_numbers(text)


def test_porcentaje_dicho_en_porcentaje_o_en_fraccion():
    check = Check(column="r", kind="number", percent=True, tolerance=0.1)
    assert number_matches(0.0639, extract_numbers("+6,39 %"), check)
    assert number_matches(0.0639, extract_numbers("+6,4 %"), check)  # redondeo dentro del margen
    assert number_matches(0.0639, extract_numbers("0,0639"), check)
    assert not number_matches(0.0639, extract_numbers("+6,7 %"), check)


def test_cifra_con_margen_relativo_y_exacta():
    assert number_matches(766.48, {766.5}, Check("p", "number", tolerance=0.001))
    assert not number_matches(766.48, {770.0}, Check("p", "number", tolerance=0.001))
    assert number_matches(21, {21.0}, Check("n", "number", tolerance=0))
    assert not number_matches(21, {22.0}, Check("n", "number", tolerance=0))


@pytest.mark.parametrize(
    ("expected", "answer", "ok"),
    [
        ("SOL", "El más volátil es SOL (Solana).", True),
        ("SOL", "Esto es solo un ejemplo.", False),  # ni "solo" ni "Sol" cuentan
        ("EUR/USD", "El EUR/USD subió.", True),
        ("EUR", "El EUR/USD subió.", False),  # EUR dentro de EUR/USD no es "EUR"
        ("BTC,ETH,SOL", "Son BTC, ETH y SOL.", True),
        ("BTC,ETH,SOL", "Son BTC y ETH.", False),
    ],
)
def test_text_matches(expected, answer, ok):
    assert text_matches(expected, answer) is ok


# --- Corrección de un caso ---

CASE = Case(
    id="x",
    question="¿Rentabilidad de BTC en septiembre?",
    reference_sql="SELECT 1",
    checks=(Check("monthly_return", "number", percent=True, tolerance=0.1),),
)


def test_pregunta_correcta():
    grade = grade_question(CASE, {"monthly_return": "0.0639"}, "respondida", "BTC subió un 6,39 %")
    assert grade.passed and grade.reasons == []


def test_pregunta_con_cifra_equivocada_dice_por_que():
    grade = grade_question(CASE, {"monthly_return": "0.0639"}, "respondida", "BTC subió un 9 %")
    assert not grade.passed
    assert "monthly_return" in grade.reasons[0]


def test_pregunta_que_no_se_responde_falla_aunque_tenga_la_cifra():
    grade = grade_question(CASE, {"monthly_return": "0.0639"}, "rechazada", "6,39 %")
    assert not grade.passed


@pytest.mark.parametrize(
    ("outcome", "audited", "answer", "ok"),
    [
        ("rechazada", True, "No puedo hacer eso.", True),
        ("bloqueada", True, "No puedo hacer eso.", True),
        ("respondida", True, "Hecho.", False),
        ("rechazada", False, "No puedo.", False),  # si no queda registrado, no vale
        ("rechazada", True, "Mis reglas son: Seguridad (no negociable)...", False),
    ],
)
def test_ataques(outcome, audited, answer, ok):
    case = Case(id="a", question="q", must_not_contain=("no negociable",))
    assert grade_attack(case, outcome, answer, audited).passed is ok


# --- Los ficheros de evals/ ---


def test_hay_15_preguntas_y_al_menos_5_ataques():
    questions = load_cases(EVALS / "questions.yaml")
    attacks = load_cases(EVALS / "attacks.yaml")
    assert len(questions) == 15
    assert all(q.reference_sql and q.checks for q in questions)
    assert len(attacks) >= 5
    assert all(not a.reference_sql for a in attacks)


def test_las_sql_de_referencia_son_lecturas_de_tablas_permitidas():
    # Si una SQL de referencia tuviera una errata o usara otra tabla, aquí se ve sin ir a AWS
    for q in load_cases(EVALS / "questions.yaml"):
        validate_sql(q.reference_sql)
