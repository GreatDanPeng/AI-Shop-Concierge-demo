"""Invented demo offers from familiar brands.

The offers do not exist in real life; they make the demo recognisable. They live in their own data files.
With CONCIERGE_BRAND_OFFERS on (the default) app/catalog.py serves ONLY the 12 brands that have a logo; off,
it serves only the six original invented stores. tests/conftest.py pins the switch to "off" for every other
test, so the rest of the suite still sees only the original catalog.
"""
import json
import re
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import engine, server
from app.assistant import UnknownStoreError, build_system_prompt, validate_store
from app.catalog import BRANDS_VARIABLE, brand_offers_on, load_offers, load_stores
from app.engine import load_members
from app.matching import estimate, match_offers
from app.tools import dispatch

TODAY = date(2026, 11, 6)
MEMBERS = {m["id"]: m for m in load_members()}
GROUPS = {"student", "teacher", "military", "nurse", "first_responder"}
BRAND_NAMES = ["Apple", "Samsung", "Best Buy", "lululemon", "Levi's", "Nike", "The North Face",
               "IKEA", "The Home Depot", "Barnes & Noble", "Marriott", "Hertz"]
BRAND_STORE_IDS = ["s7", "s8", "s9", "s10", "s11", "s12", "s14", "s15", "s16", "s17", "s18", "s19"]   # s13 (REI) is retired
ORIGINAL_STORE_IDS = {s["id"] for s in engine.load_stores()}
ORIGINAL_OFFER_IDS = {o["id"] for o in engine.load_offers()}
SAFE_MARKDOWN = re.compile(r"\[[^\[\]()\n]+\]\(#/store/[A-Za-z0-9_-]+\)")
OFFER_KEYS = {"id", "store_id", "type", "headline_bps", "groups", "excluded_items", "annual_cap_cents",
              "stackable_with_cash_back", "expires_on", "as_of", "terms"}


@pytest.fixture(autouse=True)
def brands_on(monkeypatch):
    """This file is about the brand offers, so they are on here (conftest pins them off elsewhere)."""
    monkeypatch.setenv(BRANDS_VARIABLE, "on")


def brand_stores():
    """With the brands on, the served catalog IS the brand catalog."""
    return load_stores()


def brand_offers():
    return load_offers()


def stores_by_id(result):
    return {s["store_id"]: {o["offer_id"]: o for o in s["offers"]} for s in result}


# ---------------------------------------------------------------- the switch
@pytest.mark.parametrize("value", ["off", "OFF", "Off", "0", "false", "False", "no", "NO", "  off  "])
def test_these_values_turn_the_brand_offers_off(value):
    assert brand_offers_on({BRANDS_VARIABLE: value}) is False
    assert load_stores({BRANDS_VARIABLE: value}) == engine.load_stores()
    assert load_offers({BRANDS_VARIABLE: value}) == engine.load_offers()


@pytest.mark.parametrize("environ", [{}, {BRANDS_VARIABLE: ""}, {BRANDS_VARIABLE: "   "},
                                      {BRANDS_VARIABLE: "on"}, {BRANDS_VARIABLE: "1"},
                                      {BRANDS_VARIABLE: "true"}, {BRANDS_VARIABLE: "yes"},
                                      {BRANDS_VARIABLE: "anything else"}])
def test_they_are_on_unless_explicitly_switched_off(environ):
    assert brand_offers_on(environ) is True
    assert [s["name"] for s in load_stores(environ)] == BRAND_NAMES


def test_it_reads_the_process_environment_by_default(monkeypatch):
    monkeypatch.setenv(BRANDS_VARIABLE, "off")
    assert load_stores() == engine.load_stores()
    monkeypatch.delenv(BRANDS_VARIABLE)
    assert [s["name"] for s in load_stores()] == BRAND_NAMES


# ---------------------------------------------------------------- the two catalogs
def test_with_the_brands_on_none_of_the_original_stores_or_offers_are_served():
    assert not {s["id"] for s in load_stores()} & ORIGINAL_STORE_IDS
    assert not {o["id"] for o in load_offers()} & ORIGINAL_OFFER_IDS
    assert not any(s["name"] in {"Fjordline Outdoors", "Voltage Electronics", "Inkwell Books", "Cobalt Shoes",
                                 "Harbor & Hearth", "Lumen Laptops"} for s in load_stores())


def test_with_the_brands_off_exactly_the_original_data_is_served():
    off = {BRANDS_VARIABLE: "off"}
    assert load_stores(off) == engine.load_stores() and load_offers(off) == engine.load_offers()


def test_the_twelve_brands_are_the_ones_planned_and_rei_is_gone():
    assert [s["name"] for s in brand_stores()] == BRAND_NAMES
    assert [s["id"] for s in brand_stores()] == BRAND_STORE_IDS
    assert len(brand_offers()) == 22
    assert "s13" not in {s["id"] for s in brand_stores()}
    assert not {"o22", "o23"} & {o["id"] for o in brand_offers()}              # REI's offers are retired too


def test_ids_are_unique_and_every_offer_belongs_to_a_known_store():
    stores, offers = load_stores(), load_offers()
    assert len({s["id"] for s in stores}) == len(stores)
    assert len({o["id"] for o in offers}) == len(offers)
    assert {o["store_id"] for o in offers} <= {s["id"] for s in stores}
    assert {o["id"] for o in brand_offers()}.isdisjoint(ORIGINAL_OFFER_IDS)


# ---------------------------------------------------------------- what a brand offer looks like
def test_every_brand_offer_has_the_same_fields_as_the_original_offers():
    for o in brand_offers():
        assert set(o) == OFFER_KEYS, o["id"]


def test_every_brand_offer_is_well_formed():
    for o in brand_offers():
        assert o["type"] in {"group_discount", "cash_back"}, o["id"]
        assert type(o["headline_bps"]) is int and 100 <= o["headline_bps"] <= 2000, o["id"]
        assert set(o["groups"]) <= GROUPS, o["id"]
        assert date.fromisoformat(o["as_of"]), o["id"]
        if o["type"] == "cash_back":
            assert o["groups"] == [] and o["annual_cap_cents"] is None, o["id"]
        else:
            assert o["groups"], o["id"]
        if o["annual_cap_cents"] is not None:
            assert type(o["annual_cap_cents"]) is int and o["annual_cap_cents"] > 0, o["id"]


def test_no_brand_offer_ends_in_the_future_so_the_demo_does_not_rot_on_a_date():
    for o in brand_offers():
        assert o["expires_on"] is None or date.fromisoformat(o["expires_on"]) < TODAY, o["id"]


def test_exactly_one_brand_offer_has_already_ended_and_it_is_best_buys():
    ended = [o for o in brand_offers() if o["expires_on"]]
    assert [(o["id"], o["store_id"]) for o in ended] == [("o14", "s9")]


def test_terms_are_short_plain_text_that_say_the_offer_is_invented():
    for o in brand_offers():
        terms = o["terms"]
        assert terms.endswith("Demo offer, invented for this demo."), o["id"]
        assert 0 < len(terms) <= 220, o["id"]
        assert not re.search(r"https?:|://|www\.|@|<|>|ignore|instruction|system|prompt", terms, re.I), o["id"]


def test_every_brand_store_says_in_its_blurb_that_it_is_invented():
    for s in brand_stores():
        assert "invented" in s["blurb"].lower(), s["id"]
        assert "not from the brand" in s["blurb"].lower(), s["id"]


def test_brand_stores_have_the_fields_the_page_needs_and_any_photo_follows_the_photo_rule():
    for s in brand_stores():
        assert set(s) == {"id", "name", "blurb", "category", "art", "image", "image_credit", "logo"}, s["id"]
        if s["image"] is not None:           # a licensed photo you added (docs/IMAGES.md): safe path and a credit
            assert re.fullmatch(r"/stores/[A-Za-z0-9_-]+\.(jpg|jpeg|png|webp|avif)", s["image"]), s["id"]
            assert s["image_credit"], s["id"]
        assert s["category"] in {"Outdoors", "Electronics", "Books", "Footwear", "Home", "Apparel", "Travel"}, s["id"]
        assert re.fullmatch(r"[A-Za-z0-9_-]+", s["art"]), s["id"]
        assert not re.search(r"[<>/\\]|http", s["name"]), s["id"]


# ---------------------------------------------------------------- the examples you asked for
def test_teachers_get_20_percent_off_a_new_apple_computer():
    morgan = stores_by_id(match_offers(MEMBERS["m_teacher"], TODAY))
    apple = morgan["s7"]["o10"]
    assert apple["eligible"] is True
    assert (apple["type"], apple["headline_label"]) == ("group_discount", "20%")
    assert "teacher" in apple["groups"]
    assert next(s for s in load_stores() if s["id"] == "s7")["name"] == "Apple"


def test_military_members_get_15_percent_off_at_lululemon():
    riley = stores_by_id(match_offers(MEMBERS["m_military"], TODAY))
    lulu = riley["s10"]["o16"]
    assert lulu["eligible"] is True
    assert (lulu["type"], lulu["headline_label"]) == ("group_discount", "15%")
    assert "military" in lulu["groups"]
    assert next(s for s in load_stores() if s["id"] == "s10")["name"] == "lululemon"


# ---------------------------------------------------------------- the demo members still tell a story
def test_a_member_with_an_expired_student_verification_is_told_to_renew_for_apple():
    sam = stores_by_id(match_offers(MEMBERS["m_student"], TODAY))
    assert sam["s7"]["o10"]["reasons"] == ["VERIFICATION_EXPIRED"]
    assert "renew" in sam["s7"]["o10"]["reason_text"][0].lower()


def test_an_unverified_member_is_told_to_verify_for_apple():
    jordan = stores_by_id(match_offers(MEMBERS["m_unverified"], TODAY))
    assert jordan["s7"]["o10"]["reasons"] == ["NOT_VERIFIED"]


def test_an_unverified_member_still_gets_the_cash_back_offers():
    jordan = stores_by_id(match_offers(MEMBERS["m_unverified"], TODAY))
    eligible = sorted(oid for store in jordan.values() for oid, o in store.items()
                      if o["eligible"] and oid in {x["id"] for x in brand_offers()})
    assert eligible and all(next(x for x in brand_offers() if x["id"] == oid)["type"] == "cash_back"
                            for oid in eligible)


def test_best_buys_ended_offer_is_explained_as_ended_and_never_listed():
    morgan = stores_by_id(match_offers(MEMBERS["m_teacher"], TODAY))
    assert morgan["s9"]["o14"]["reasons"] == ["OFFER_EXPIRED"]
    listed = dispatch("list_all_eligible_offers", {}, member_id="m_teacher", today=TODAY)["offers"]
    assert "o14" not in [o["offer_id"] for o in listed]
    assert "o15" in [o["offer_id"] for o in listed]            # the cash back there is still fine


def test_the_apple_cap_limits_the_discount():
    r = estimate(MEMBERS["m_teacher"], "s7", 300000, TODAY)    # a $3,000 cart, a $2,500 cap
    assert r["dollars"] == {"cart": "$3,000.00", "group_discount": "$500.00", "you_pay": "$2,500.00",
                            "cash_back": "$0.00", "total_savings": "$500.00"}


def test_marriotts_discount_does_not_combine_with_its_cash_back():
    r = estimate(MEMBERS["m_military"], "s18", 100000, TODAY)
    assert r["group_discount"]["cents"] == 15000 and r["cash_back"] is None
    assert r["dollars"]["you_pay"] == "$850.00"


# ---------------------------------------------------------------- through the tools
def test_the_all_offers_tool_lists_brand_offers_with_safe_links():
    offers = dispatch("list_all_eligible_offers", {}, member_id="m_teacher", today=TODAY)["offers"]
    links = {o["offer_id"]: o["link_markdown"] for o in offers}
    assert links["o10"] == "[Apple: 20% off](#/store/s7)"
    assert links["o28"] == "[Barnes & Noble: 20% off](#/store/s17)"
    assert links["o18"] == "[Levi's: 20% off](#/store/s11)"
    assert links["o32"] == "[Hertz: 12% off](#/store/s19)"
    assert links["o25"] == "[IKEA: 10% off](#/store/s15)"
    assert all(SAFE_MARKDOWN.fullmatch(link) for link in links.values())


def test_a_store_page_tool_call_for_a_brand_store_works():
    r = dispatch("get_eligible_offers", {"store_id": "s7"}, member_id="m_teacher", today=TODAY)
    assert [o["offer_id"] for o in r["offers"]] == ["o10"]
    assert r["offers"][0]["link_markdown"] == "[Apple: 20% off](#/store/s7)"
    assert r["offers"][0]["annual_cap_dollars"] == "$2,500.00"


def test_the_best_deals_list_starts_with_the_biggest_brand_offers():
    offers = dispatch("list_all_eligible_offers", {}, member_id="m_teacher", today=TODAY)["offers"]
    assert [o["offer_id"] for o in offers[:4]] == ["o10", "o18", "o24", "o28"]   # the four 20% offers, by id
    assert max(o["headline_bps"] for o in brand_offers()) == 2000


def test_tools_still_take_no_member_id_and_still_refuse_one():
    r = dispatch("list_all_eligible_offers", {"member_id": "m_student"}, member_id="m_teacher", today=TODAY)
    assert r == {"error": "forbidden_argument"}


# ---------------------------------------------------------------- through the server and the assistant
def sign_in(client, member_id):
    assert client.post("/demo/switch-member", json={"member_id": member_id}).status_code == 200


def test_the_discounts_endpoint_lists_the_twelve_brand_stores_and_nothing_else():
    client = TestClient(server.app)
    sign_in(client, "m_teacher")
    body = client.get("/discounts").json()
    assert [s["store_id"] for s in body["stores"]] == BRAND_STORE_IDS
    assert [s["name"] for s in body["stores"]] == BRAND_NAMES


def test_the_estimate_endpoint_knows_a_brand_store_and_the_same_figures_come_back():
    client = TestClient(server.app)
    sign_in(client, "m_teacher")
    r = client.get("/estimate", params={"store_id": "s7", "cart_cents": 300000})
    assert r.status_code == 200
    assert r.json()["dollars"]["group_discount"] == "$500.00"


def test_with_the_brands_off_a_brand_store_is_unknown(monkeypatch):
    monkeypatch.setenv(BRANDS_VARIABLE, "off")
    client = TestClient(server.app)
    sign_in(client, "m_teacher")
    assert client.get("/estimate", params={"store_id": "s7", "cart_cents": 300000}).status_code == 400
    assert [s["store_id"] for s in client.get("/discounts").json()["stores"]] == [f"s{i}" for i in range(1, 7)]
    with pytest.raises(UnknownStoreError):
        validate_store("s7")


def test_the_assistant_knows_the_brand_stores_when_they_are_on():
    assert validate_store("s7") == "s7"
    prompt = build_system_prompt("s7")
    for name in BRAND_NAMES:
        assert name in prompt
    assert "currently viewing s7 (Apple)" in prompt
    assert "Fjordline Outdoors" not in prompt and "Lumen Laptops" not in prompt


def test_with_the_brands_on_an_original_store_is_unknown_to_the_server_and_the_assistant():
    client = TestClient(server.app)
    sign_in(client, "m_teacher")
    assert client.get("/estimate", params={"store_id": "s1", "cart_cents": 20000}).status_code == 400
    with pytest.raises(UnknownStoreError):
        validate_store("s1")
    with pytest.raises(UnknownStoreError):
        build_system_prompt("s1")


def test_the_prompt_says_every_offer_is_invented_even_with_a_real_brand_name():
    flat = " ".join(build_system_prompt(None).split())
    assert re.search(r"every store and offer in this demo is invented", flat, re.I)
    assert re.search(r"even when a store uses a real brand name", flat, re.I)
    assert re.search(r"say plainly that it is an invented demo offer", flat, re.I)


def test_the_brand_data_files_are_plain_json_arrays():
    for name in ("brand_stores.json", "brand_offers.json"):
        data = json.loads((engine.DATA_DIR / name).read_text(encoding="utf-8"))
        assert isinstance(data, list) and data
