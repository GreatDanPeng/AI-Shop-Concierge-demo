"""The model sees ONE date: the tool result's own "as_of" (written before the fix).

An eval run found answers that said "as of 2026-11-06" and "as of 2026-11-08" in the same breath: the model
sometimes quoted the date stamped on an offer in the data files (when someone typed the offer in) instead of
the live date the tool result carries. The data stamp is bookkeeping, not "today", so it is no longer passed
on. The data files keep the field.
"""
import json
from datetime import date

import pytest

from app.catalog import BRANDS_VARIABLE, load_stores
from app.engine import load_members
from app.tools import dispatch

TODAY = date(2026, 11, 6)
MEMBERS = [m["id"] for m in load_members()]


@pytest.fixture(autouse=True)
def brands_on(monkeypatch):
    monkeypatch.setenv(BRANDS_VARIABLE, "on")


def offers_of(result):
    return result["offers"]


@pytest.mark.parametrize("member", MEMBERS)
@pytest.mark.parametrize("tool", ["get_eligible_offers", "list_store_offers"])
def test_no_offer_in_a_store_result_carries_its_own_date(member, tool):
    for store in load_stores():
        result = dispatch(tool, {"store_id": store["id"]}, member_id=member, today=TODAY)
        assert result["as_of"] == "2026-11-06"
        assert all("as_of" not in o for o in offers_of(result)), (tool, store["id"])


@pytest.mark.parametrize("member", MEMBERS)
def test_no_offer_in_the_all_offers_result_carries_its_own_date(member):
    result = dispatch("list_all_eligible_offers", {}, member_id=member, today=TODAY)
    assert result["as_of"] == "2026-11-06"
    assert result["offers"] and all("as_of" not in o for o in result["offers"])


def test_a_date_stamped_in_the_data_never_reaches_the_model():
    offer = {"id": "x1", "store_id": "s1", "type": "cash_back", "headline_bps": 100, "groups": [],
             "excluded_items": [], "annual_cap_cents": None, "stackable_with_cash_back": True,
             "expires_on": None, "as_of": "1999-01-01", "terms": "ok"}
    stores = [{"id": "s1", "name": "Only One"}]
    for name, args in [("get_eligible_offers", {"store_id": "s1"}), ("list_store_offers", {"store_id": "s1"}),
                       ("list_all_eligible_offers", {})]:
        dumped = json.dumps(dispatch(name, args, member_id="m_nurse", today=TODAY, offers=[offer], stores=stores))
        assert "1999-01-01" not in dumped, name
        assert "2026-11-06" in dumped, name


def test_the_data_files_keep_the_field_for_whoever_maintains_them():
    from app.catalog import load_offers
    assert all("as_of" in o for o in load_offers())
