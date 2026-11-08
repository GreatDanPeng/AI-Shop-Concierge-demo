"""The "as of" date comes from the real calendar, unless CONCIERGE_TODAY pins it.

Written before app/clock.py. The rules engine keeps its fixed DEMO_TODAY as the default argument
(the starter tests rely on it); only the server and the assistant loop use the live date.
"""
import json
import logging
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import server
from app.assistant import run_assistant
from app.clock import PIN_VARIABLE, today
from tests.fakes import FakeClient, end_turn, tool_turn, tool_use_block


# ---------------------------------------------------------------- the clock itself
def test_without_a_pin_it_is_the_real_date():
    before = date.today()
    got = today({})
    after = date.today()
    assert before <= got <= after


def test_the_real_date_comes_from_the_injected_source():
    assert today({}, real=lambda: date(2030, 1, 2)) == date(2030, 1, 2)


def test_a_pin_wins_over_the_real_date():
    assert today({PIN_VARIABLE: "2026-11-06"}, real=lambda: date(2030, 1, 2)) == date(2026, 11, 6)


def test_a_pin_may_have_spaces_around_it():
    assert today({PIN_VARIABLE: "  2026-11-06  "}) == date(2026, 11, 6)


@pytest.mark.parametrize("blank", ["", "   "])
def test_a_blank_pin_means_no_pin(blank):
    assert today({PIN_VARIABLE: blank}, real=lambda: date(2030, 1, 2)) == date(2030, 1, 2)


@pytest.mark.parametrize("bad", [
    "tomorrow", "2026-13-40", "2026-02-30", "2026-1-6", "20261106", "2026-W45-5",
    "2026-11-06T10:00", "2026-11-06 extra", "６０２６-１１-０６", "-2026-11-06", "0000-00-00",
])
def test_a_bad_pin_is_ignored_and_the_value_is_never_logged(bad, caplog):
    with caplog.at_level(logging.DEBUG):
        got = today({PIN_VARIABLE: bad}, real=lambda: date(2030, 1, 2))
    assert got == date(2030, 1, 2)
    assert PIN_VARIABLE in caplog.text                       # says which setting is wrong
    assert bad.strip() not in caplog.text                    # but never repeats what it held


def test_it_reads_the_process_environment_by_default(monkeypatch):
    monkeypatch.setenv(PIN_VARIABLE, "2027-01-01")
    assert today() == date(2027, 1, 1)


# ---------------------------------------------------------------- the web API uses it
@pytest.fixture
def web():
    client = TestClient(server.app)
    return client


def sign_in(client, member_id):
    assert client.post("/demo/switch-member", json={"member_id": member_id}).status_code == 200


def test_discounts_and_estimate_carry_the_pinned_date(web, monkeypatch):
    monkeypatch.setenv(PIN_VARIABLE, "2026-12-01")
    sign_in(web, "m_nurse")
    assert web.get("/discounts").json()["as_of"] == "2026-12-01"
    estimate = web.get("/estimate", params={"store_id": "s1", "cart_cents": 20000}).json()
    assert estimate["as_of"] == "2026-12-01"


def test_without_a_pin_the_api_shows_the_real_date(web, monkeypatch):
    monkeypatch.delenv(PIN_VARIABLE)
    sign_in(web, "m_nurse")
    before = date.today()
    got = date.fromisoformat(web.get("/discounts").json()["as_of"])
    assert before <= got <= date.today()


def test_the_date_is_read_per_request_so_a_long_running_server_moves_on(web, monkeypatch):
    sign_in(web, "m_nurse")
    monkeypatch.setenv(PIN_VARIABLE, "2026-11-06")
    assert web.get("/discounts").json()["as_of"] == "2026-11-06"
    monkeypatch.setenv(PIN_VARIABLE, "2026-11-07")
    assert web.get("/discounts").json()["as_of"] == "2026-11-07"


def _lumen_offers(web):
    stores = {s["store_id"]: s for s in web.get("/discounts").json()["stores"]}
    return {o["offer_id"]: o["eligible"] for o in stores["s6"]["offers"]}


def test_the_date_changes_what_a_member_qualifies_for(web, monkeypatch):
    """Offer o9 ends 2026-12-31: matching must follow the clock, not the old fixed date."""
    sign_in(web, "m_teacher")
    monkeypatch.setenv(PIN_VARIABLE, "2026-12-31")
    assert _lumen_offers(web) == {"o9": True}
    monkeypatch.setenv(PIN_VARIABLE, "2027-01-01")
    assert _lumen_offers(web) == {"o9": False}


def test_members_verification_status_follows_the_clock(web, monkeypatch):
    monkeypatch.setenv(PIN_VARIABLE, "2027-03-02")           # a day after the nurse's 365 days
    sign_in(web, "m_nurse")
    [verification] = web.get("/me").json()["verifications"]
    assert verification["status"] == "expired"
    [listed] = [m for m in web.get("/demo/members").json() if m["id"] == "m_nurse"]
    assert listed["verifications"] == [{"group": "nurse", "status": "expired"}]


# ---------------------------------------------------------------- the assistant uses it
def _tool_result_sent(client):
    [block] = client.calls[1]["messages"][-1]["content"]
    return json.loads(block["content"])


@pytest.mark.usefixtures("configured_env")
def test_tool_results_reach_the_model_with_the_pinned_date(monkeypatch):
    monkeypatch.setenv(PIN_VARIABLE, "2026-12-01")
    client = FakeClient(tool_turn(tool_use_block("get_eligible_offers", {"store_id": "s1"})),
                        end_turn("done"))
    run_assistant("what can I get?", "m_nurse", "s1", client=client)
    assert _tool_result_sent(client)["as_of"] == "2026-12-01"


@pytest.mark.usefixtures("configured_env")
def test_the_assistant_applies_the_live_date_to_eligibility_too(monkeypatch):
    monkeypatch.setenv(PIN_VARIABLE, "2027-01-01")           # o9 has ended by then
    client = FakeClient(tool_turn(tool_use_block("get_eligible_offers", {"store_id": "s6"})),
                        end_turn("done"))
    run_assistant("what can I get?", "m_teacher", "s6", client=client)
    assert _tool_result_sent(client)["offers"] == []


@pytest.mark.usefixtures("configured_env")
def test_every_tool_call_in_one_answer_uses_the_same_day(monkeypatch):
    """The date is read once per question, so a midnight rollover cannot split one answer."""
    days = iter([date(2026, 12, 1), date(2026, 12, 2), date(2026, 12, 3)])
    from app import assistant
    monkeypatch.setattr(assistant, "clock_today", lambda: next(days))
    client = FakeClient(
        tool_turn(tool_use_block("get_eligible_offers", {"store_id": "s1"}, id="a"),
                  tool_use_block("explain_ineligibility", {"offer_id": "o1"}, id="b")),
        end_turn("done"))
    run_assistant("hi", "m_nurse", "s1", client=client)
    blocks = client.calls[1]["messages"][-1]["content"]
    assert [json.loads(b["content"])["as_of"] for b in blocks] == ["2026-12-01", "2026-12-01"]
