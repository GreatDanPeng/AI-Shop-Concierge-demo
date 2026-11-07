"""Tests for the list_store_offers tool (the offer catalog).

Why it exists: explain_ineligibility needs an offer_id, but get_eligible_offers only
lists offers the member CAN use. Without a catalog the model would have to guess the id
of an offer it is not eligible for. The catalog is public data, the same for every
member, and it never carries the untrusted terms text.
"""
import json
from datetime import date

import pytest

from app.engine import load_members
from app.tools import FORBIDDEN_ARGS, TOOLS, dispatch

TODAY = date(2026, 11, 6)
MEMBER_IDS = [m["id"] for m in load_members()]


def call(args, member="m_nurse", **kwargs):
    return dispatch("list_store_offers", args, member_id=member, today=TODAY, **kwargs)


def offer_ids(result):
    return sorted(o["offer_id"] for o in result["offers"])


# ---- the point of the tool ----
def test_lists_offers_the_member_cannot_use():
    # m_military hit the annual cap on o1, so only o2 is eligible...
    eligible = dispatch("get_eligible_offers", {"store_id": "s1"}, member_id="m_military", today=TODAY)
    assert [o["offer_id"] for o in eligible["offers"]] == ["o2"]
    # ...but the catalog still shows o1, so the model can ask explain_ineligibility about it.
    assert offer_ids(call({"store_id": "s1"}, member="m_military")) == ["o1", "o2"]


def test_catalog_is_the_same_for_every_member():
    results = [offer_ids(call({"store_id": "s1"}, member=m)) for m in MEMBER_IDS]
    assert all(r == ["o1", "o2"] for r in results)


def test_expired_and_group_restricted_offers_are_listed():
    offers = [
        {"id": "x1", "store_id": "sx", "type": "group_discount", "headline_bps": 2000,
         "groups": ["military"], "expires_on": "2020-01-01", "terms": "ended"},
        {"id": "x2", "store_id": "sx", "type": "cash_back", "headline_bps": 100, "terms": "ok"},
        {"id": "y1", "store_id": "other", "type": "cash_back", "headline_bps": 500, "terms": "elsewhere"},
    ]
    r = call({"store_id": "sx"}, offers=offers)
    assert offer_ids(r) == ["x1", "x2"]          # expired and not-eligible are still listed; other stores are not
    expired = next(o for o in r["offers"] if o["offer_id"] == "x1")
    assert expired["expires_on"] == "2020-01-01"  # the model can see why it may be gone


def test_result_shape_and_public_fields():
    r = call({"store_id": "s1"})
    assert r["store_id"] == "s1" and r["as_of"] == "2026-11-06"
    o1 = next(o for o in r["offers"] if o["offer_id"] == "o1")
    assert o1["type"] == "group_discount"
    assert o1["headline_percent"] == 30
    assert o1["annual_cap_cents"] == 800000
    assert o1["groups"] == ["nurse", "teacher", "military", "first_responder"]  # what to verify
    assert o1["stackable_with_cash_back"] is True


def test_unknown_store_gives_an_empty_list_not_an_error():
    assert call({"store_id": "nope"}) == {"store_id": "nope", "as_of": "2026-11-06", "offers": []}


# ---- security: untrusted text and personal data ----
def test_catalog_never_carries_the_untrusted_terms_text():
    r = call({"store_id": "s5"})                       # s5 holds the prompt-injection fixture o99
    assert "o99" in offer_ids(r)                       # the offer is listed...
    dumped = json.dumps(r)
    assert "terms_untrusted" not in dumped             # ...but its terms text is not
    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" not in dumped
    for o in r["offers"]:
        assert "terms_untrusted" not in o and "terms" not in o


@pytest.mark.parametrize("member", MEMBER_IDS)
def test_catalog_contains_no_personal_data(member):
    names = {m["id"]: m for m in load_members()}[member]
    for store in ("s1", "s2", "s5"):
        out = json.dumps(call({"store_id": store}, member=member))
        assert names["display_name"] not in out
        assert "example.invalid" not in out


# ---- member binding and argument validation (same rules as every tool) ----
@pytest.mark.parametrize("forbidden", sorted(FORBIDDEN_ARGS))
def test_forbidden_arguments_are_refused(forbidden):
    assert call({"store_id": "s1", forbidden: "m_student"}) == {"error": "forbidden_argument"}


@pytest.mark.parametrize("bad", [{}, {"store_id": 5}, {"store_id": None}, {"store_id": ["s1"]}, "s1", None])
def test_bad_arguments_are_rejected(bad):
    assert call(bad) == {"error": "bad_arguments"}


def test_unknown_member_is_rejected():
    assert call({"store_id": "s1"}, member="nobody") == {"error": "unknown_member"}


# ---- the tool schema the model sees ----
def test_schema_is_registered_and_takes_only_a_store_id():
    tool = next((t for t in TOOLS if t["name"] == "list_store_offers"), None)
    assert tool is not None, "list_store_offers must be in TOOLS"
    schema = tool["input_schema"]
    assert schema["type"] == "object"
    assert list(schema["properties"]) == ["store_id"]
    assert schema["required"] == ["store_id"]
    assert not (FORBIDDEN_ARGS & set(schema["properties"]))
    assert tool["description"].strip()


def test_tool_names_are_unique():
    names = [t["name"] for t in TOOLS]
    assert len(names) == len(set(names))
