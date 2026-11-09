import json
from pathlib import Path

from app.engine import load_members, load_stores
from evals.checks import check_answer

QUESTIONS = json.loads((Path(__file__).resolve().parent.parent / "evals" / "questions.json")
                       .read_text(encoding="utf-8"))


def test_check_answer_include_and_forbidden():
    q = {"must_include": ["30%", "as of"], "must_not_include": ["90%"]}
    assert check_answer("30% off, as of Nov 6", q) == []
    assert check_answer("90% off!", q) == ["missing: 30%", "missing: as of", "forbidden: 90%"]


def test_check_answer_is_case_insensitive():
    assert check_answer("AS OF today", {"must_include": ["as of"]}) == []


def test_questions_reference_real_members_and_stores():
    members = {m["id"] for m in load_members()}
    stores = {s["id"] for s in load_stores()}
    for q in QUESTIONS:
        assert q["member_id"] in members
        assert q["store_id"] is None or q["store_id"] in stores
