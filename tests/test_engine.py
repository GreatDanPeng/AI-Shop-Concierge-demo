"""Starter tests for the rules engine. Read each one, then add your own.

Dates: the demo's "today" is 2026-11-06 (app.engine.DEMO_TODAY).
"""
from datetime import date

import pytest

from app.engine import (best_combination, eligible_offers, explain_ineligibility,
                        load_members, load_offers, pct_half_up, verification_status)

TODAY = date(2026, 11, 6)
MEMBERS = {m["id"]: m for m in load_members()}
OFFERS = {o["id"]: o for o in load_offers()}


def ids(offers):
    return sorted(o["id"] for o in offers)


# ---- rounding ----
def test_half_up_rounding():
    assert pct_half_up(5, 1000) == 1    # 0.5 -> 1 (round() would give 0)
    assert pct_half_up(4, 1000) == 0    # 0.4 -> 0
    assert pct_half_up(15, 1000) == 2   # 1.5 -> 2


# ---- verification ----
def test_verification_boundary_is_365_days():
    member = {"verifications": {"student": "2025-11-06"}}
    assert verification_status(member, "student", date(2026, 11, 5)) == "valid"    # 364 days
    assert verification_status(member, "student", date(2026, 11, 6)) == "expired"  # 365 days


def test_missing_and_future_verification():
    assert verification_status({"verifications": {}}, "nurse", TODAY) == "missing"
    assert verification_status({"verifications": {"nurse": "2027-01-01"}}, "nurse", TODAY) == "missing"


# ---- eligibility by member ----
def test_nurse_gets_group_and_cash_back_at_s1():
    assert ids(eligible_offers(MEMBERS["m_nurse"], "s1", TODAY)) == ["o1", "o2"]


def test_unverified_member_gets_cash_back_only():
    assert ids(eligible_offers(MEMBERS["m_unverified"], "s1", TODAY)) == ["o2"]


def test_expired_student_verification_is_explained():
    student = MEMBERS["m_student"]
    assert explain_ineligibility(student, OFFERS["o3"], TODAY) == ["VERIFICATION_EXPIRED"]
    assert ids(eligible_offers(student, "s2", TODAY)) == ["o4"]  # cash back still works


def test_unverified_reason_code():
    assert explain_ineligibility(MEMBERS["m_unverified"], OFFERS["o1"], TODAY) == ["NOT_VERIFIED"]


def test_cap_reached_is_explained():
    assert explain_ineligibility(MEMBERS["m_military"], OFFERS["o1"], TODAY) == ["CAP_REACHED"]


def test_offer_expiry_boundary():
    nurse_student = {"id": "x", "verifications": {"student": "2026-10-01"}}
    assert explain_ineligibility(nurse_student, OFFERS["o9"], date(2026, 12, 31)) == []
    assert explain_ineligibility(nurse_student, OFFERS["o9"], date(2027, 1, 1)) == ["OFFER_EXPIRED"]


# ---- best combination ----
def test_best_combination_nurse_at_s1():
    r = best_combination(MEMBERS["m_nurse"], "s1", 20000, TODAY)
    assert r["group_discount"]["cents"] == 6000          # 30% of $200.00
    assert r["you_pay_cents"] == 14000
    assert r["cash_back_cents"] == 490                   # 3.5% of the $140.00 paid
    assert r["total_savings_cents"] == 6490


def test_non_stackable_offer_drops_cash_back():
    teacher = {"id": "t", "verifications": {"teacher": "2026-09-01"}}
    r = best_combination(teacher, "s2", 10000, TODAY)    # o3 15% (no cash back) beats o4 2% alone
    assert r["group_discount"]["cents"] == 1500
    assert r["cash_back"] is None


def test_cap_limits_the_discounted_part_of_the_cart():
    near_cap = {"id": "x", "verifications": {"nurse": "2026-03-01"},
                "annual_spend_cents": {"o1": 700000}}    # $1,000 of cap left
    r = best_combination(near_cap, "s1", 200000, TODAY)  # cart $2,000
    assert r["group_discount"]["cents"] == 30000         # 30% of the remaining $1,000 only
    assert r["you_pay_cents"] == 170000


def test_cash_back_only_member():
    r = best_combination(MEMBERS["m_student"], "s2", 10000, TODAY)
    assert r["group_discount"] is None
    assert r["cash_back_cents"] == 200


@pytest.mark.parametrize("bad", [0, -1, True, 1.5, "100"])
def test_bad_cart_values_are_rejected(bad):
    with pytest.raises(ValueError):
        best_combination(MEMBERS["m_nurse"], "s1", bad, TODAY)
