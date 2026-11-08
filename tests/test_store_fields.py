"""Stores carry what the page needs to draw a tile: a category, an illustration key, and an optional photo.

The photo is for licensed images you add yourself (see docs/IMAGES.md). Nothing is downloaded or scraped.
"""
import re
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import server
from app.engine import load_members, load_stores
from app.matching import match_offers

TODAY = date(2026, 11, 6)
CATEGORIES = {"Outdoors", "Electronics", "Books", "Footwear", "Home"}
ART_KEYS = {"tent", "headphones", "books", "sneaker", "lamp", "laptop"}
MEMBERS = {m["id"]: m for m in load_members()}


@pytest.mark.parametrize("store", load_stores(), ids=lambda s: s["id"])
def test_every_store_has_a_known_category_and_illustration(store):
    assert store["category"] in CATEGORIES
    assert store["art"] in ART_KEYS


@pytest.mark.parametrize("store", load_stores(), ids=lambda s: s["id"])
def test_the_photo_fields_exist_and_are_safe(store):
    assert "image" in store and "image_credit" in store
    image = store["image"]
    if image is not None:
        # a file you add under web/public/stores/, referenced by a plain path: no urls, no traversal
        assert re.fullmatch(r"/stores/[A-Za-z0-9_-]+\.(jpg|jpeg|png|webp|avif)", image), image
        assert store["image_credit"], "a photo needs a credit line"


def test_the_categories_group_stores_the_way_a_shopper_would_browse():
    by_category = {}
    for store in load_stores():
        by_category.setdefault(store["category"], []).append(store["name"])
    assert by_category["Electronics"] == ["Voltage Electronics", "Lumen Laptops"]
    assert len(by_category) == 5


def test_match_offers_passes_the_store_fields_through():
    result = match_offers(MEMBERS["m_nurse"], TODAY)
    by_id = {s["store_id"]: s for s in result}
    assert by_id["s1"]["category"] == "Outdoors" and by_id["s1"]["art"] == "tent"
    assert by_id["s6"]["category"] == "Electronics" and by_id["s6"]["art"] == "laptop"
    for s in result:
        assert {"category", "art", "image", "image_credit"} <= set(s)


def test_the_discounts_endpoint_carries_them_too():
    client = TestClient(server.app)
    assert client.post("/demo/switch-member", json={"member_id": "m_nurse"}).status_code == 200
    stores = client.get("/discounts").json()["stores"]
    assert [s["category"] for s in stores] == ["Outdoors", "Electronics", "Books", "Footwear", "Home", "Electronics"]
    assert all(s["image"] is None for s in stores)       # no photos yet: the page draws the illustration
