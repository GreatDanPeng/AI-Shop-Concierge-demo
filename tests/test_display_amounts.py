"""Ready-made dollar amounts in tool results, so the model never converts cents itself.

Why: a live run with a real model turned 130000 cents into "$130.00" (instead of $1,300.00) and
4900 cents into "$4.90" (instead of $49.00), even though the tool results were right. Prices must be
quoted, not re-derived, so the tools now carry the dollar strings and the prompt says to copy them.
"""
import json
import re
from datetime import date

import pytest

from app.assistant import SYSTEM_RULES, build_system_prompt, run_assistant
from app.engine import load_members
from app.money import format_cents
from app.tools import dispatch
from tests.fakes import FakeClient, end_turn, tool_turn, tool_use_block

pytestmark = pytest.mark.usefixtures("configured_env")  # fake credentials for the one loop test

TODAY = date(2026, 11, 6)
MEMBER_IDS = [m["id"] for m in load_members()]
DOLLARS = re.compile(r"(-?)\$(\d{1,3}(?:,\d{3})*|\d+)\.(\d{2})")


def cents_of(text):
    """Parse '$1,300.00' back to 130000 (and check the shape: two decimals, commas in the right places)."""
    m = DOLLARS.fullmatch(text)
    assert m, f"not a well-formed dollar amount: {text!r}"
    value = int(m.group(2).replace(",", "")) * 100 + int(m.group(3))
    return -value if m.group(1) else value


def best(member, store, cart):
    return dispatch("best_combination", {"store_id": store, "cart_cents": cart},
                    member_id=member, today=TODAY)


# ---------------------------------------------------------------- the formatter
@pytest.mark.parametrize("cents, text", [
    (0, "$0.00"), (1, "$0.01"), (5, "$0.05"), (99, "$0.99"), (100, "$1.00"), (490, "$4.90"),
    (4900, "$49.00"), (14000, "$140.00"), (64900, "$649.00"), (99999, "$999.99"),
    (100000, "$1,000.00"), (130000, "$1,300.00"), (150000, "$1,500.00"), (800000, "$8,000.00"),
    (123456789, "$1,234,567.89"), (100000000, "$1,000,000.00"), (-250, "-$2.50"),
])
def test_format_cents(cents, text):
    assert format_cents(cents) == text


@pytest.mark.parametrize("bad", [1.5, "100", None, True, False])
def test_format_cents_only_accepts_integers(bad):
    with pytest.raises(TypeError):
        format_cents(bad)


def test_formatting_then_parsing_always_gives_back_the_same_cents():
    # A dropped or added digit (the real mistake) would break this for some value.
    values = list(range(0, 3_000_000, 997)) + [1, 9, 10, 99, 100, 101, 999, 1000, 9999, 10000, 99999,
                                               100000, 100001, 999999, 1000000, 12345678]
    for cents in values:
        assert cents_of(format_cents(cents)) == cents


# ---------------------------------------------------------------- best_combination carries dollars
def test_the_cases_that_went_wrong_live_now_carry_the_exact_dollar_strings():
    books = best("m_teacher", "s3", 150000)          # pay 130000 cents: the model said "$130.00"
    assert books["dollars"] == {"cart": "$1,500.00", "group_discount": "$200.00",
                                "you_pay": "$1,300.00", "cash_back": "$0.00",
                                "total_savings": "$200.00"}
    gear = best("m_nurse", "s1", 200000)             # cash back 4900 cents: the model said "$4.90"
    assert gear["dollars"] == {"cart": "$2,000.00", "group_discount": "$600.00",
                               "you_pay": "$1,400.00", "cash_back": "$49.00",
                               "total_savings": "$649.00"}


def test_the_small_cart_case_that_always_worked_still_works():
    assert best("m_nurse", "s1", 20000)["dollars"] == {
        "cart": "$200.00", "group_discount": "$60.00", "you_pay": "$140.00",
        "cash_back": "$4.90", "total_savings": "$64.90"}


def test_no_group_discount_is_shown_as_zero_dollars():
    r = best("m_military", "s1", 30000)               # the annual cap is reached: cash back only
    assert r["dollars"] == {"cart": "$300.00", "group_discount": "$0.00", "you_pay": "$300.00",
                            "cash_back": "$10.50", "total_savings": "$10.50"}


def test_the_cents_are_still_there_and_unchanged():
    r = best("m_nurse", "s1", 200000)
    assert (r["you_pay_cents"], r["cash_back_cents"], r["total_savings_cents"]) == (140000, 4900, 64900)
    assert r["group_discount"]["cents"] == 60000


@pytest.mark.parametrize("member", MEMBER_IDS)
@pytest.mark.parametrize("store", ["s1", "s2", "s3", "s4", "s5", "s6"])
def test_every_dollar_string_agrees_with_its_cents_for_every_member_store_and_cart(member, store):
    for cart in (1, 99, 100, 12345, 99999, 100000, 150000, 999999, 5_000_000):
        r = best(member, store, cart)
        d = r["dollars"]
        group = r["group_discount"]["cents"] if r["group_discount"] else 0
        assert cents_of(d["cart"]) == r["cart_cents"] == cart
        assert cents_of(d["group_discount"]) == group
        assert cents_of(d["you_pay"]) == r["you_pay_cents"]
        assert cents_of(d["cash_back"]) == r["cash_back_cents"]
        assert cents_of(d["total_savings"]) == r["total_savings_cents"]


def test_errors_are_unchanged_and_carry_no_amounts():
    assert dispatch("best_combination", {"store_id": "s1", "cart_cents": 0}, member_id="m_nurse") == {
        "error": "bad_arguments"}
    assert dispatch("best_combination", {"store_id": "s1", "cart_cents": 1, "member_id": "x"},
                    member_id="m_nurse") == {"error": "forbidden_argument"}


# ---------------------------------------------------------------- offers carry the cap in dollars
@pytest.mark.parametrize("tool", ["get_eligible_offers", "list_store_offers"])
def test_offers_show_the_annual_cap_in_dollars(tool):
    offers = {o["offer_id"]: o for o in dispatch(tool, {"store_id": "s1"}, member_id="m_nurse",
                                                 today=TODAY)["offers"]}
    assert offers["o1"]["annual_cap_cents"] == 800000
    assert offers["o1"]["annual_cap_dollars"] == "$8,000.00"
    assert offers["o2"]["annual_cap_dollars"] is None          # cash back has no cap
    s3 = dispatch(tool, {"store_id": "s3"}, member_id="m_nurse", today=TODAY)["offers"]
    assert s3[0]["annual_cap_dollars"] == "$1,000.00"


# ---------------------------------------------------------------- the model is told to copy them
def test_the_prompt_says_to_quote_the_dollar_strings_and_never_convert_cents():
    prompt = build_system_prompt(None)
    assert '"dollars"' in prompt
    assert "annual_cap_dollars" in prompt
    assert "never convert" in prompt.lower()


def test_the_prompt_no_longer_teaches_a_cents_to_dollars_pattern_the_model_can_misapply():
    assert "490 ->" not in SYSTEM_RULES                       # '490 -> $4.90' looked like 4900 -> $4.90
    assert "14000 ->" not in SYSTEM_RULES


def test_the_dollar_strings_reach_the_model_inside_the_tool_result():
    cart = {"store_id": "s3", "cart_cents": 150000}
    client = FakeClient(tool_turn(tool_use_block("best_combination", cart)), end_turn("done"))
    run_assistant("I need $1,500 of books. What do I pay?", "m_teacher", "s3", client=client)
    [block] = client.calls[1]["messages"][-1]["content"]
    assert json.loads(block["content"])["dollars"]["you_pay"] == "$1,300.00"
