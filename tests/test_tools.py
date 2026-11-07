"""Tests for the tool layer: member binding, minimal data, untrusted text."""
import json
from datetime import date

from app.engine import load_members
from app.tools import TOOLS, dispatch

TODAY = date(2026, 11, 6)


def call(name, args, member="m_nurse"):
    return dispatch(name, args, member_id=member, today=TODAY)


def test_returns_only_this_members_eligible_offers():
    r = call("get_eligible_offers", {"store_id": "s1"})
    assert sorted(o["offer_id"] for o in r["offers"]) == ["o1", "o2"]
    assert r["as_of"] == "2026-11-06"


def test_model_cannot_pass_a_member_id():
    r = call("get_eligible_offers", {"store_id": "s1", "member_id": "m_student"})
    assert r == {"error": "forbidden_argument"}


def test_no_tool_schema_asks_for_a_member_id():
    for tool in TOOLS:
        assert "member_id" not in tool["input_schema"]["properties"]


def test_unknown_member_and_unknown_tool():
    assert call("get_eligible_offers", {"store_id": "s1"}, member="nobody") == {"error": "unknown_member"}
    assert call("delete_everything", {}) == {"error": "unknown_tool"}


def test_results_contain_no_personal_data():
    for m in load_members():
        out = json.dumps(call("get_eligible_offers", {"store_id": "s5"}, member=m["id"]))
        assert m["display_name"] not in out
        assert "example.invalid" not in out


def test_injection_text_is_labeled_untrusted_and_never_used_for_math():
    r = call("get_eligible_offers", {"store_id": "s5"})
    bad = next(o for o in r["offers"] if o["offer_id"] == "o99")
    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" in bad["terms_untrusted"]   # the data is present...
    combo = call("best_combination", {"store_id": "s5", "cart_cents": 10000})
    assert combo["group_discount"]["offer_id"] == "o8"                    # ...but only rules decide
    assert "90%" not in json.dumps(combo)


def test_bad_arguments_are_rejected():
    assert call("best_combination", {"store_id": "s1", "cart_cents": True}) == {"error": "bad_arguments"}
    assert call("best_combination", {"store_id": "s1", "cart_cents": 0}) == {"error": "bad_arguments"}
    assert call("get_eligible_offers", {"store_id": 5}) == {"error": "bad_arguments"}
    assert call("explain_ineligibility", {"offer_id": "nope"}) == {"error": "unknown_offer"}


def test_explain_ineligibility_for_capped_member():
    r = call("explain_ineligibility", {"offer_id": "o1"}, member="m_military")
    assert r["eligible"] is False and r["reasons"] == ["CAP_REACHED"]
