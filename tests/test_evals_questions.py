"""The question set is well formed (written before the new questions were added).

A malformed question would fail every run for the wrong reason, so the shape is checked here, offline.
"""
import json
from pathlib import Path

import pytest

from app import engine
from app.catalog import load_stores
from app.engine import load_members
from app.tools import TOOLS
from evals.checks import LINK_MODES

QUESTIONS = json.loads((Path(__file__).resolve().parent.parent / "evals" / "questions.json")
                       .read_text(encoding="utf-8"))
KNOWN_KEYS = {"id", "member_id", "store_id", "question", "must_include", "must_not_include", "must_call_tool",
              "must_not_call_tool", "links", "min_links", "catalog"}
TOOL_NAMES = {t["name"] for t in TOOLS}
ORIGINAL_STORES = {s["id"] for s in engine.load_stores()}
ALL_STORES = {s["id"] for s in load_stores({})}          # brands on
MEMBERS = {m["id"] for m in load_members()}
BY_ID = {q["id"]: q for q in QUESTIONS}


def test_ids_are_unique_and_run_q1_to_q20():
    assert [q["id"] for q in QUESTIONS] == [f"q{i}" for i in range(1, 21)]


@pytest.mark.parametrize("q", QUESTIONS, ids=lambda q: q["id"])
def test_every_question_is_well_formed(q):
    assert set(q) <= KNOWN_KEYS, set(q) - KNOWN_KEYS
    assert {"id", "member_id", "store_id", "question"} <= set(q)
    assert q["member_id"] in MEMBERS
    assert isinstance(q["question"], str) and 0 < len(q["question"].strip()) and len(q["question"]) <= 2000
    catalog = q.get("catalog", "original")
    assert catalog in {"original", "brands"}
    assert q["store_id"] is None or q["store_id"] in (ALL_STORES if catalog == "brands" else ORIGINAL_STORES)
    assert set(q.get("must_call_tool", [])) <= TOOL_NAMES
    assert set(q.get("must_not_call_tool", [])) <= TOOL_NAMES
    assert q.get("links", "server_only") in LINK_MODES
    assert q.get("min_links", 1) >= 1 and type(q.get("min_links", 1)) is int


@pytest.mark.parametrize("q", QUESTIONS, ids=lambda q: q["id"])
def test_every_question_checks_something(q):
    checks = ("must_include", "must_not_include", "must_call_tool", "must_not_call_tool", "links", "min_links")
    assert any(q.get(key) for key in checks)


def test_price_questions_must_get_their_numbers_from_best_combination():
    for qid in ("q8", "q9", "q10"):
        assert "best_combination" in BY_ID[qid]["must_call_tool"], qid


def test_the_original_expectations_of_the_first_ten_questions_are_untouched():
    assert BY_ID["q1"]["must_include"] == ["30%", "3.5%", "as of"]
    assert BY_ID["q9"]["must_include"] == ["$1,300.00"] and BY_ID["q9"]["must_not_include"] == ["$130.00"]
    assert BY_ID["q10"]["must_include"] == ["$1,400.00", "$49.00"]


def test_best_deals_with_no_store_must_use_the_all_offers_tool_and_link_only_what_the_server_offered():
    for qid in ("q11", "q12"):
        q = BY_ID[qid]
        assert q["store_id"] is None and q["must_call_tool"] == ["list_all_eligible_offers"], qid
        assert q["links"] == "server_only" and q["min_links"] >= 1, qid


def test_the_brand_questions_use_the_brand_catalog_and_the_rest_do_not():
    brands = {q["id"] for q in QUESTIONS if q.get("catalog") == "brands"}
    assert brands == {"q17", "q18", "q19", "q20"}


def test_the_privacy_and_injection_questions_exist_and_forbid_leaks():
    assert "riley" in BY_ID["q13"]["must_not_include"]
    assert {"example.invalid", "@"} <= set(BY_ID["q16"]["must_not_include"])


def test_the_questions_are_not_duplicates_of_each_other():
    texts = [(q["member_id"], q["store_id"], q["question"]) for q in QUESTIONS]
    assert len(set(texts)) == len(texts)
