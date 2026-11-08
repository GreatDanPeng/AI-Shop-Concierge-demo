"""Shared fixtures. One is autouse: it pins the demo date (see below); the rest are opt-in."""
import pytest

from tests.fakes import DispatchSpy


@pytest.fixture(autouse=True)
def pinned_demo_date(monkeypatch):
    """Hold "today" at the old fixed demo date (2026-11-06) for every test.

    The server now uses the real calendar date, so without a pin the tests that assert dates and
    eligibility would change meaning as time passes. Tests of the clock itself set or clear the
    variable again on their own.
    """
    monkeypatch.setenv("CONCIERGE_TODAY", "2026-11-06")


@pytest.fixture(autouse=True)
def original_catalog_only(monkeypatch):
    """Switch the invented brand offers off for every test, so the suite sees the original six stores.

    The app shows the brand offers by default (for demos). Only tests/test_brand_catalog.py turns them on.
    """
    monkeypatch.setenv("CONCIERGE_BRAND_OFFERS", "off")


@pytest.fixture
def configured_env(monkeypatch):
    """Fake credentials and a fake model id, so the assistant never needs the real ones."""
    monkeypatch.setenv("ANTHROPIC_MODEL", "test-model-from-env")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    # Tests must not depend on the developer's shell (for example an OpenRouter setup).
    for name in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
                 "OPENROUTER_API_KEY", "OPENROUTER_MODEL", "LLM_PROVIDER"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def dispatch_spy(monkeypatch):
    """Replace app.assistant.dispatch with a spy that records its calls and runs the real one."""
    from app import assistant, tools
    spy = DispatchSpy(tools.dispatch)
    monkeypatch.setattr(assistant, "dispatch", spy)
    return spy
