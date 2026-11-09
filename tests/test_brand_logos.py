"""Each brand store shows its brand's own logo (written before the files and the field existed).

A logo is a small SVG under web/public/brands/, named by the store's `logo` path. The illustration (`art`)
stays as the fallback, and REI has no free logo file, so its `logo` is null. The files come from two
sources recorded in web/public/brands/SOURCES.md. SVG can carry scripts and outside links, so every file is
inspected here, and a file that fails is not allowed into the project.
"""
import re
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import engine, server
from app.catalog import BRANDS_VARIABLE, load_stores
from app.engine import load_members
from app.matching import match_offers

ROOT = Path(__file__).resolve().parent.parent
BRANDS = ROOT / "web" / "public" / "brands"
TODAY = date(2026, 11, 6)
LOGO_PATH = re.compile(r"/brands/[A-Za-z0-9_-]+\.(svg|png|webp)")
EXPECTED = {
    "Apple": "apple.svg", "Samsung": "samsung.svg", "Best Buy": "bestbuy.svg", "lululemon": "lululemon.svg",
    "Levi's": "levis.svg", "Nike": "nike.svg", "REI": None, "The North Face": "thenorthface.svg",
    "IKEA": "ikea.svg", "The Home Depot": "homedepot.svg", "Barnes & Noble": "barnesandnoble.svg",
    "Marriott": "marriott.svg", "Hertz": "hertz.svg",
}
# `style` and `use` are allowed only in their harmless forms, checked separately below: a stylesheet that loads
# nothing, and a `use` that points at something inside the same file.
FORBIDDEN_TAGS = {"script", "foreignobject", "image", "text", "tspan", "a", "iframe", "object", "embed",
                  "animate", "set", "audio", "video", "link"}


@pytest.fixture(autouse=True)
def brands_on(monkeypatch):
    monkeypatch.setenv(BRANDS_VARIABLE, "on")


def brand_stores():
    return load_stores()[len(engine.load_stores()):]


# ---------------------------------------------------------------- the data
def test_every_brand_store_has_a_logo_field_and_only_rei_has_none():
    stores = {s["name"]: s for s in brand_stores()}
    assert set(stores) == set(EXPECTED)
    for name, store in stores.items():
        assert "logo" in store, name
        expected = EXPECTED[name]
        assert store["logo"] == (f"/brands/{expected}" if expected else None), name
    assert [n for n, s in stores.items() if s["logo"] is None] == ["REI"]


def test_a_logo_path_is_a_plain_path_under_brands_never_an_address():
    for s in brand_stores():
        if s["logo"] is not None:
            assert LOGO_PATH.fullmatch(s["logo"]), s["logo"]


def test_every_logo_names_its_own_file_and_each_file_exists():
    paths = [s["logo"] for s in brand_stores() if s["logo"]]
    assert len(set(paths)) == len(paths) == 12
    for path in paths:
        assert (ROOT / "web" / "public" / path.lstrip("/")).is_file(), path


def test_the_original_six_stores_are_untouched_and_have_no_logo():
    assert all("logo" not in s for s in engine.load_stores())


def test_the_illustration_stays_as_the_fallback_for_every_brand_store():
    assert all(s["art"] for s in brand_stores())


# ---------------------------------------------------------------- the files
def svg_files():
    return sorted(BRANDS.glob("*.svg"))


def parsed(path):
    text = path.read_text(encoding="utf-8")
    assert "<!doctype" not in text.lower() and "<!entity" not in text.lower(), path.name   # no entity tricks
    return text, ET.fromstring(text)


def local(tag):
    return tag.rsplit("}", 1)[-1].lower()


def test_there_is_exactly_one_svg_per_logo_and_nothing_else_in_the_folder():
    names = {s["logo"].rsplit("/", 1)[-1] for s in brand_stores() if s["logo"]}
    assert {p.name for p in svg_files()} == names
    assert {p.name for p in BRANDS.iterdir()} == names | {"SOURCES.md", "SIMPLE_ICONS_LICENSE.md"}


@pytest.mark.parametrize("path", svg_files(), ids=lambda p: p.name)
def test_each_svg_holds_only_drawing_shapes(path):
    _, root = parsed(path)
    assert local(root.tag) == "svg"
    tags = {local(el.tag) for el in root.iter()}
    assert not tags & FORBIDDEN_TAGS, tags & FORBIDDEN_TAGS
    assert tags & {"path", "rect", "circle", "ellipse", "polygon", "polyline", "line"}   # it draws something


@pytest.mark.parametrize("path", svg_files(), ids=lambda p: p.name)
def test_a_stylesheet_in_an_svg_loads_nothing_and_a_use_points_only_inside_the_file(path):
    _, root = parsed(path)
    for el in root.iter():
        if local(el.tag) == "style":
            assert not re.search(r"url\(\s*['\"]?(?!#)|@import|expression|javascript:", el.text or "", re.I)
        if local(el.tag) == "use":
            refs = [v for k, v in el.attrib.items() if k.rsplit("}", 1)[-1].lower() == "href"]
            assert refs and all(r.startswith("#") for r in refs), refs


@pytest.mark.parametrize("path", svg_files(), ids=lambda p: p.name)
def test_no_svg_has_event_handlers_scripts_or_outside_links(path):
    text, root = parsed(path)
    for el in root.iter():
        for name, value in el.attrib.items():
            key = name.rsplit("}", 1)[-1].lower()
            assert not key.startswith("on"), (el.tag, name)
            if key == "href":
                assert value.startswith("#"), (el.tag, name, value)         # only a link to itself
            if key == "style":
                assert not re.search(r"url\(\s*['\"]?(?!#)|@import|expression|javascript:", value, re.I), value
    assert not re.search(r"javascript:|data:text/html|@import|https?://(?!www\.w3\.org/|purl\.org/|creativecommons\.org/|"
                         r"inkscape\.org/|sodipodi\.sourceforge\.net/|ns\.adobe\.com/)", text, re.I)


@pytest.mark.parametrize("path", svg_files(), ids=lambda p: p.name)
def test_each_svg_is_small_and_knows_its_size(path):
    _, root = parsed(path)
    assert path.stat().st_size <= 20_000
    assert root.get("viewBox") or (root.get("width") and root.get("height"))


def test_sources_are_written_down_next_to_the_files():
    sources = (BRANDS / "SOURCES.md").read_text(encoding="utf-8")
    for path in svg_files():
        line = next((l for l in sources.splitlines() if path.name in l), None)
        assert line, f"{path.name} is not listed in SOURCES.md"
        assert "https://" in line, path.name
        assert re.search(r"CC0|Public domain", line), path.name
    assert "trademark" in sources.lower()
    assert "REI" in sources                                               # says why it has no logo


# ---------------------------------------------------------------- through the app
def test_match_offers_carries_the_logo_for_brand_stores_and_none_for_the_original_six():
    result = {s["name"]: s for s in match_offers(load_members()[0], TODAY)}
    assert result["Apple"]["logo"] == "/brands/apple.svg"
    assert result["REI"]["logo"] is None
    assert result["Fjordline Outdoors"]["logo"] is None


def test_the_discounts_endpoint_carries_the_logo_too():
    client = TestClient(server.app)
    assert client.post("/demo/switch-member", json={"member_id": "m_teacher"}).status_code == 200
    stores = {s["name"]: s for s in client.get("/discounts").json()["stores"]}
    assert stores["Nike"]["logo"] == "/brands/nike.svg" and stores["REI"]["logo"] is None
    assert all("logo" in s for s in stores.values())
