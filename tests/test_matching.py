"""Identity matching: the user stories, as tests. Deterministic code only; no model involved."""
import json
from datetime import date

import pytest

from app import matching
from app.engine import load_members, load_offers
from app.matching import describe_identity, estimate, headline_label, match_offers

TODAY = date(2026, 11, 6)
MEMBERS = {m["id"]: m for m in load_members()}


def matches(member_id, **kwargs):
    return match_offers(MEMBERS[member_id], TODAY, **kwargs)


def offers_in(result, store_id):
    store = next(s for s in result if s["store_id"] == store_id)
    return {o["offer_id"]: o for o in store["offers"]}


# ---------------------------------------------------------------- the demo cast
def test_there_is_a_demo_member_for_each_story():
    assert {"m_student", "m_military", "m_teacher", "m_unverified", "m_nurse"} <= set(MEMBERS)
    assert MEMBERS["m_teacher"]["verifications"] == {"teacher": "2026-09-01"}


# ---------------------------------------------------------------- who am I
@pytest.mark.parametrize("member_id, expected", [
    ("m_nurse", [("nurse", "valid", "2026-03-01", "2027-03-01")]),
    ("m_student", [("student", "expired", "2025-08-15", "2026-08-15")]),
    ("m_teacher", [("teacher", "valid", "2026-09-01", "2027-09-01")]),
    ("m_military", [("military", "valid", "2026-05-10", "2027-05-10")]),
    ("m_unverified", []),
])
def test_identity_lists_each_verified_group_with_its_status_and_expiry(member_id, expected):
    identity = describe_identity(MEMBERS[member_id], TODAY)
    got = [(v["group"], v["status"], v["verified_on"], v["expires_on"]) for v in identity["verifications"]]
    assert got == expected
    assert identity["member_id"] == member_id
    assert identity["display_name"] == MEMBERS[member_id]["display_name"]


def test_identity_never_includes_the_email():
    for member in MEMBERS.values():
        dumped = json.dumps(describe_identity(member, TODAY))
        assert member["email"] not in dumped
        assert "example.invalid" not in dumped


def test_a_verification_dated_in_the_future_is_reported_as_missing():
    member = {"id": "x", "display_name": "X", "email": "x@example.invalid",
              "verifications": {"nurse": "2027-01-01"}, "annual_spend_cents": {}}
    [only] = describe_identity(member, TODAY)["verifications"]
    assert only["status"] == "missing"


# ---------------------------------------------------------------- the stories
def test_unverified_jordan_sees_why_the_30_percent_offer_is_not_available():
    o1 = offers_in(matches("m_unverified"), "s1")["o1"]
    assert o1["eligible"] is False
    assert o1["reasons"] == ["NOT_VERIFIED"]
    [text] = o1["reason_text"]
    assert "nurse" in text
    assert "first responder" in text  # the groups that would qualify
    assert offers_in(matches("m_unverified"), "s1")["o2"]["eligible"] is True   # cash back for everyone


def test_student_sam_sees_the_expired_verification_but_keeps_cash_back():
    s2 = offers_in(matches("m_student"), "s2")
    assert s2["o3"]["reasons"] == ["VERIFICATION_EXPIRED"]
    assert "renew" in s2["o3"]["reason_text"][0].lower()
    assert s2["o4"]["eligible"] is True


def test_military_riley_sees_the_annual_cap_on_the_30_percent_offer():
    s1 = offers_in(matches("m_military"), "s1")
    assert s1["o1"]["reasons"] == ["CAP_REACHED"]
    assert "cap" in s1["o1"]["reason_text"][0].lower()
    assert s1["o2"]["eligible"] is True
    s4 = offers_in(matches("m_military"), "s4")                    # elsewhere the status still helps
    assert s4["o6"]["eligible"] is True


def test_teacher_morgan_matches_the_teacher_offers_everywhere():
    result = matches("m_teacher")
    assert offers_in(result, "s1")["o1"]["eligible"] is True
    assert offers_in(result, "s2")["o3"]["eligible"] is True
    assert offers_in(result, "s3")["o5"]["eligible"] is True
    assert offers_in(result, "s6")["o9"]["eligible"] is True
    assert offers_in(result, "s4")["o6"]["eligible"] is False     # military/first responder/nurse only


def test_nurse_avery_at_a_glance():
    result = matches("m_nurse")
    eligible = {sid: sorted(oid for oid, o in offers_in(result, sid).items() if o["eligible"])
                for sid in ("s1", "s2", "s3", "s4", "s5", "s6")}
    assert eligible == {"s1": ["o1", "o2"], "s2": ["o4"], "s3": ["o5"], "s4": ["o6", "o7"],
                        "s5": ["o8", "o99"], "s6": []}


# ---------------------------------------------------------------- shape and safety of the payload
def test_every_store_is_listed_in_order_with_its_offers():
    result = matches("m_nurse")
    assert [s["store_id"] for s in result] == ["s1", "s2", "s3", "s4", "s5", "s6"]
    assert all({"store_id", "name", "blurb", "offers"} <= set(s) for s in result)
    assert sum(len(s["offers"]) for s in result) == len(load_offers())


def test_each_offer_has_what_the_page_needs_and_nothing_untrusted():
    for s in matches("m_nurse"):
        for o in s["offers"]:
            assert set(o) == {"offer_id", "type", "headline_bps", "headline_label", "groups",
                              "excluded_items", "annual_cap_cents", "annual_cap_dollars",
                              "stackable_with_cash_back",
                              "expires_on", "eligible", "reasons", "reason_text"}
            assert type(o["headline_bps"]) is int
            assert len(o["reason_text"]) == len(o["reasons"])
            assert o["eligible"] == (o["reasons"] == [])


def test_no_terms_text_no_injection_text_and_no_personal_data_in_any_payload():
    for member in MEMBERS.values():
        dumped = json.dumps(matches(member["id"]))
        assert "IGNORE ALL PREVIOUS" not in dumped
        assert "terms" not in dumped
        assert member["email"] not in dumped
        assert member["display_name"] not in dumped


def test_several_reasons_each_get_their_own_text_in_the_engines_order():
    offers = [{"id": "x1", "store_id": "s1", "type": "group_discount", "headline_bps": 2000,
               "groups": ["military"], "expires_on": "2020-01-01", "terms": "t"}]
    [s1] = [s for s in matches("m_unverified", offers=offers) if s["store_id"] == "s1"]
    [offer] = s1["offers"]
    assert offer["reasons"] == ["NOT_VERIFIED", "OFFER_EXPIRED"]
    assert len(offer["reason_text"]) == 2
    assert "ended" in offer["reason_text"][1].lower()


def test_an_unknown_reason_code_still_gets_a_safe_sentence(monkeypatch):
    monkeypatch.setattr(matching, "explain_ineligibility", lambda member, offer, today: ["BRAND_NEW_CODE"])
    [s1] = [s for s in matches("m_nurse") if s["store_id"] == "s1"]
    assert s1["offers"][0]["reason_text"] == ["This offer is not available to you right now."]


@pytest.mark.parametrize("bps, label", [(3000, "30%"), (350, "3.5%"), (375, "3.75%"), (1250, "12.5%"),
                                        (305, "3.05%"), (100, "1%"), (5, "0.05%")])
def test_the_headline_label_is_built_from_integers(bps, label):
    assert headline_label(bps) == label


# ---------------------------------------------------------------- cart estimates (the engine decides)
def test_nurse_estimate_at_the_outdoor_store():
    r = estimate(MEMBERS["m_nurse"], "s1", 20000, TODAY)
    assert (r["you_pay_cents"], r["cash_back_cents"], r["total_savings_cents"]) == (14000, 490, 6490)
    assert r["as_of"] == "2026-11-06"
    assert r["assumptions"]


def test_teacher_electronics_the_group_discount_does_not_combine_with_cash_back():
    r = estimate(MEMBERS["m_teacher"], "s2", 40000, TODAY)
    assert r["group_discount"]["offer_id"] == "o3"
    assert (r["you_pay_cents"], r["cash_back_cents"], r["total_savings_cents"]) == (34000, 0, 6000)
    assert r["cash_back"] is None


def test_teacher_books_the_annual_cap_limits_the_discounted_part_of_the_cart():
    r = estimate(MEMBERS["m_teacher"], "s3", 150000, TODAY)
    assert r["group_discount"]["cents"] == 20000                    # 20% of the first $1,000 only
    assert (r["you_pay_cents"], r["total_savings_cents"]) == (130000, 20000)


def test_military_riley_after_the_cap_only_cash_back_is_left():
    r = estimate(MEMBERS["m_military"], "s1", 30000, TODAY)
    assert r["group_discount"] is None
    assert (r["you_pay_cents"], r["cash_back_cents"]) == (30000, 1050)


def test_student_sam_with_an_expired_verification_gets_cash_back_only():
    r = estimate(MEMBERS["m_student"], "s2", 10000, TODAY)
    assert r["group_discount"] is None
    assert r["cash_back_cents"] == 200


@pytest.mark.parametrize("bad", [0, -1, True, 1.5, "100"])
def test_a_bad_cart_value_is_rejected(bad):
    with pytest.raises(ValueError):
        estimate(MEMBERS["m_nurse"], "s1", bad, TODAY)
