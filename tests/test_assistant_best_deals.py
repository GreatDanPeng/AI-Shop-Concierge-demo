"""A general "best deals" question with no store chosen must be answered, not turned into a question.

Written before the prompt rule. The wording of a prompt cannot be proven by a unit test, so these
check that the rule is there and that the tool call it asks for works through the real loop; how
often a real model follows it is measured separately with a live run.
"""
import json
import re
from datetime import date

import pytest

from app.assistant import build_system_prompt, run_assistant
from app.tools import dispatch as real_dispatch
from tests.fakes import FakeClient, end_turn, tool_turn, tool_use_block

pytestmark = pytest.mark.usefixtures("configured_env")

TOOL = "list_all_eligible_offers"
TODAY = date(2026, 11, 6)  # conftest pins CONCIERGE_TODAY to this day


def flat(text):
    """The text with every run of whitespace as one space: line wrapping is not behaviour."""
    return " ".join(text.split())


def section(prompt, start, end):
    return flat(prompt[prompt.index(start):prompt.index(end)])


# ---------------------------------------------------------------- the rule in the prompt
@pytest.mark.parametrize("store", [None, "s1"])
def test_the_prompt_names_the_tool_in_its_scope(store):
    scope = section(build_system_prompt(store), "SCOPE", "FACTS COME FROM TOOLS")
    assert TOOL in scope


def test_the_prompt_says_not_to_ask_which_store_for_a_general_question():
    prompt = flat(build_system_prompt(None))
    assert re.search(r"best deals or discounts in general", prompt, re.I)
    assert re.search(r"do not ask which store", prompt, re.I)
    assert re.search(rf"call {TOOL}", prompt)


def test_the_rule_applies_only_when_no_store_is_named_or_viewed():
    prompt = flat(build_system_prompt(None))
    assert re.search(r"no store is named and none is being viewed", prompt, re.I)
    assert re.search(r"named or viewed store[^.]*get_eligible_offers", prompt, re.I)


def test_the_answer_is_short_linked_and_leads_to_a_cart_total():
    rule = section(build_system_prompt(None), "BEST DEALS", "UNTRUSTED TEXT")
    assert re.search(r"at most five", rule, re.I)
    assert "link_markdown" in rule
    assert re.search(r"largest percentage first", rule, re.I)   # says what the order means
    assert re.search(r"cart total", rule, re.I)                 # offers to work out real savings


def test_the_prompt_still_carries_no_web_address_and_no_date():
    prompt = build_system_prompt(None)
    assert "http" not in prompt.lower()
    assert "2026-11-06" not in prompt


# ---------------------------------------------------------------- the call through the real loop
def ask_best_deals(member, **kwargs):
    client = FakeClient(tool_turn(tool_use_block(TOOL, {})), end_turn("done"))
    result = run_assistant("Show my best deals", member, None, client=client, **kwargs)
    [block] = client.calls[1]["messages"][-1]["content"]
    return client, result, block


@pytest.mark.parametrize("member", ["m_unverified", "m_nurse", "m_teacher"])
def test_the_tool_result_reaches_the_model_exactly_as_the_tool_made_it(member):
    _, _, block = ask_best_deals(member)
    assert json.loads(block["content"]) == real_dispatch(TOOL, {}, member_id=member, today=TODAY)
    assert "is_error" not in block


def test_the_session_member_is_bound_even_with_no_store(dispatch_spy):
    ask_best_deals("m_nurse")
    [call] = dispatch_spy.calls
    assert call["name"] == TOOL and call["args"] == {}
    assert call["kwargs"]["member_id"] == "m_nurse"


def test_a_member_id_sneaked_into_the_call_comes_back_as_an_error():
    client = FakeClient(tool_turn(tool_use_block(TOOL, {"member_id": "m_student"}, id="tu_9")),
                        end_turn("done"))
    result = run_assistant("Show my best deals", "m_nurse", None, client=client)
    [block] = client.calls[1]["messages"][-1]["content"]
    assert block["is_error"] is True and block["tool_use_id"] == "tu_9"
    assert json.loads(block["content"]) == {"error": "forbidden_argument"}
    assert [c["error"] for c in result.tool_calls] == ["forbidden_argument"]


def test_it_uses_the_live_date_like_every_other_tool(monkeypatch):
    monkeypatch.setenv("CONCIERGE_TODAY", "2027-01-01")        # Lumen Laptops 12% has ended by then
    _, _, block = ask_best_deals("m_teacher")
    sent = json.loads(block["content"])
    assert sent["as_of"] == "2027-01-01"
    assert "o9" not in [o["offer_id"] for o in sent["offers"]]
