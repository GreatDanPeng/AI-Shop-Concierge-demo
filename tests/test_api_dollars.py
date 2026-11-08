"""The web API owns every money string, so the page never converts cents itself.

Same reason as for the model: a converted amount can drop a digit. The server formats once (integer
math in app/money.py); the tool, the matching service and the web API all use that one function.
"""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import server
from app.engine import load_members
from app.matching import estimate, match_offers
from app.money import with_dollars
from app.tools import dispatch

TODAY = date(2026, 11, 6)
MEMBERS = {m["id"]: m for m in load_members()}


@pytest.fixture
def client():
    return TestClient(server.app)


def sign_in(client, member_id):
    assert client.post("/demo/switch-member", json={"member_id": member_id}).status_code == 200
    return client


def test_with_dollars_adds_one_key_and_leaves_the_engine_result_alone():
    engine_result = {"cart_cents": 150000, "group_discount": {"offer_id": "o5", "cents": 20000},
                     "cash_back": None, "you_pay_cents": 130000, "cash_back_cents": 0,
                     "total_savings_cents": 20000}
    out = with_dollars(engine_result)
    assert out["dollars"] == {"cart": "$1,500.00", "group_discount": "$200.00", "you_pay": "$1,300.00",
                              "cash_back": "$0.00", "total_savings": "$200.00"}
    assert "dollars" not in engine_result                   # a copy, not a mutation
    assert {k: v for k, v in out.items() if k != "dollars"} == engine_result


def test_the_estimate_service_carries_dollars():
    r = estimate(MEMBERS["m_teacher"], "s3", 150000, TODAY)
    assert r["dollars"]["you_pay"] == "$1,300.00"
    assert r["dollars"]["total_savings"] == "$200.00"


@pytest.mark.parametrize("member, store, cart", [("m_nurse", "s1", 20000), ("m_nurse", "s1", 200000),
                                                 ("m_teacher", "s2", 40000), ("m_military", "s1", 30000)])
def test_the_model_tool_and_the_page_service_give_identical_dollars(member, store, cart):
    via_tool = dispatch("best_combination", {"store_id": store, "cart_cents": cart},
                        member_id=member, today=TODAY)
    via_service = estimate(MEMBERS[member], store, cart, TODAY)
    assert via_tool == via_service


def test_matched_offers_carry_the_annual_cap_in_dollars():
    stores = {s["store_id"]: {o["offer_id"]: o for o in s["offers"]}
              for s in match_offers(MEMBERS["m_nurse"], TODAY)}
    assert stores["s1"]["o1"]["annual_cap_cents"] == 800000
    assert stores["s1"]["o1"]["annual_cap_dollars"] == "$8,000.00"
    assert stores["s3"]["o5"]["annual_cap_dollars"] == "$1,000.00"
    assert stores["s1"]["o2"]["annual_cap_dollars"] is None        # cash back has no cap


def test_the_estimate_endpoint_returns_dollars(client):
    sign_in(client, "m_teacher")
    body = client.get("/estimate", params={"store_id": "s3", "cart_cents": 150000}).json()
    assert body["dollars"] == {"cart": "$1,500.00", "group_discount": "$200.00", "you_pay": "$1,300.00",
                               "cash_back": "$0.00", "total_savings": "$200.00"}
    assert body["you_pay_cents"] == 130000                          # the cents are still there


def test_the_discounts_endpoint_returns_cap_dollars(client):
    sign_in(client, "m_nurse")
    s1 = client.get("/discounts").json()["stores"][0]["offers"]
    assert {o["offer_id"]: o["annual_cap_dollars"] for o in s1} == {"o1": "$8,000.00", "o2": None}
