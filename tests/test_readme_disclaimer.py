"""The README carries the trademark disclaimer, and it names every brand whose logo the project shows.

Written before the disclaimer. If a logo is added without updating the disclaimer, this fails.
"""
import re
from pathlib import Path

from app.catalog import load_stores

README = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")


def disclaimer():
    lines = README.splitlines()
    start = next(i for i, line in enumerate(lines) if "Disclaimer:" in line)
    end = start
    while end + 1 < len(lines) and lines[end + 1].strip():
        end += 1
    return " ".join(" ".join(lines[start:end + 1]).split())


def test_the_disclaimer_is_the_last_section_of_the_readme():
    headings = [line for line in README.splitlines() if line.startswith("## ")]
    assert headings[-1] == "## Disclaimer"
    assert "Disclaimer:" in README.split("## Disclaimer", 1)[1]


def test_it_says_what_the_project_is_for_who_owns_the_marks_and_that_there_is_no_commercial_use():
    text = disclaimer()
    assert re.search(r"intended solely for personal learning and technical practice", text)
    assert re.search(r"trademarks, logos and brand elements", text)
    assert re.search(r"property of their respective owners", text)
    assert "Apple Inc." in text
    assert re.search(r"not used for any commercial purposes", text)


def test_it_says_the_offers_are_invented_and_that_no_brand_is_involved():
    text = disclaimer()
    assert re.search(r"offers shown are invented", text)
    assert re.search(r"no sponsorship, endorsement or affiliation with any brand, or with ID\.me, is implied", text)


def test_it_names_every_brand_whose_logo_is_shown():
    text = disclaimer()
    with_logo = [s["name"] for s in load_stores({}) if s.get("logo")]
    assert len(with_logo) == 12
    for name in with_logo:
        assert name in text, name
