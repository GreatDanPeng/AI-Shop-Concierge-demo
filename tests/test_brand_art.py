"""The pictures the data asks for are pictures the page can draw (written before the illustrations).

Reads the art keys straight from web/src/design/StoreArt.tsx, so a store can never name a drawing that
does not exist, and the brand stores each have a picture of their own.
"""
import re
from pathlib import Path

import pytest

from app import engine
from app.catalog import BRANDS_VARIABLE, load_stores

STORE_ART = Path(__file__).resolve().parent.parent / "web" / "src" / "design" / "StoreArt.tsx"
DRAWN = set(re.findall(r"^  (\w+): \(<>", STORE_ART.read_text(encoding="utf-8"), re.M))


@pytest.fixture(autouse=True)
def brands_on(monkeypatch):
    monkeypatch.setenv(BRANDS_VARIABLE, "on")


def test_the_source_lists_the_pictures_it_can_draw():
    assert {"tent", "headphones", "books", "sneaker", "lamp", "laptop", "bag"} <= DRAWN


@pytest.mark.parametrize("store", load_stores({}), ids=lambda s: s["id"])
def test_every_store_names_a_picture_the_page_can_draw(store):
    assert store["art"] in DRAWN, store["name"]


def test_each_brand_store_has_a_picture_of_its_own():
    brand = load_stores()[len(engine.load_stores()):]
    arts = [s["art"] for s in brand]
    assert len(set(arts)) == len(arts) == 13
    assert not set(arts) & {s["art"] for s in engine.load_stores()}      # none is one of the original six
    assert "bag" not in arts                                              # and none is the fallback
