"""Provider selection: OpenRouter (cheap models for testing) or Anthropic, chosen by the environment.

The rule that matters most: a credential for one provider must never be sent to the other.
No network and no real keys here.
"""
import json

import pytest

from app.assistant import (CLIENT_RETRIES, CLIENT_TIMEOUT, OPENROUTER_BASE_URL, ConfigError,
                           build_client, provider_status, require_model, resolve_provider,
                           run_assistant)
from tests.fakes import FakeClient, end_turn

pytestmark = pytest.mark.usefixtures("configured_env")  # Anthropic key and model; OpenRouter unset

OR_KEY = "or-test-key-not-real"
OR_MODEL = "deepseek/deepseek-v4.1-flash-1017"


@pytest.fixture
def openrouter(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", OR_KEY)
    monkeypatch.setenv("OPENROUTER_MODEL", OR_MODEL)


# ---------------------------------------------------------------- which provider
def test_anthropic_is_the_default_when_no_openrouter_key_is_set():
    assert resolve_provider() == "anthropic"


def test_an_openrouter_key_selects_openrouter_even_if_an_anthropic_key_exists(openrouter):
    assert resolve_provider() == "openrouter"       # cheap by default; ANTHROPIC_API_KEY is also set


@pytest.mark.parametrize("blank", ["", "   "])
def test_a_blank_openrouter_key_does_not_select_openrouter(monkeypatch, blank):
    monkeypatch.setenv("OPENROUTER_API_KEY", blank)
    assert resolve_provider() == "anthropic"


def test_an_explicit_choice_always_wins(openrouter, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    assert resolve_provider() == "anthropic"
    monkeypatch.delenv("OPENROUTER_API_KEY")
    monkeypatch.setenv("LLM_PROVIDER", "  OpenRouter ")     # case and spaces do not matter
    assert resolve_provider() == "openrouter"


def test_an_unknown_provider_is_a_config_error_that_does_not_echo_the_value(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "some-other-vendor")
    with pytest.raises(ConfigError, match="LLM_PROVIDER") as caught:
        resolve_provider()
    assert "some-other-vendor" not in str(caught.value)


# ---------------------------------------------------------------- the model id
def test_the_openrouter_model_comes_from_openrouter_model(openrouter):
    assert require_model() == OR_MODEL


def test_the_openrouter_model_is_required_and_anthropics_is_not_a_fallback(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", OR_KEY)        # ANTHROPIC_MODEL is still set
    with pytest.raises(ConfigError, match="OPENROUTER_MODEL"):
        require_model()


def test_the_loop_sends_the_openrouter_model_to_the_api(openrouter):
    client = FakeClient(end_turn("hi"))
    run_assistant("hello", "m_nurse", "s1", client=client)
    assert client.calls[0]["model"] == OR_MODEL


def test_a_missing_openrouter_model_stops_before_any_call(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", OR_KEY)
    client = FakeClient(end_turn("hi"))
    with pytest.raises(ConfigError, match="OPENROUTER_MODEL"):
        run_assistant("hello", "m_nurse", "s1", client=client)
    assert client.calls == []


# ---------------------------------------------------------------- the client
def test_the_openrouter_client_uses_its_endpoint_a_bearer_token_and_the_usual_limits(openrouter):
    client = build_client()
    assert str(client.base_url).startswith(OPENROUTER_BASE_URL)
    assert client.auth_headers == {"Authorization": f"Bearer {OR_KEY}"}
    assert client.timeout == CLIENT_TIMEOUT
    assert client.max_retries == CLIENT_RETRIES


def test_an_anthropic_credential_is_never_sent_to_openrouter(openrouter, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "SECRET-ANTHROPIC-KEY")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "SECRET-ANTHROPIC-TOKEN")
    client = build_client()
    sent = json.dumps(dict(client.auth_headers))
    assert "SECRET-ANTHROPIC" not in sent
    assert OR_KEY in sent
    assert client.api_key is None


def test_a_base_url_in_the_environment_cannot_redirect_the_openrouter_key(openrouter, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://elsewhere.invalid")
    assert str(build_client().base_url).startswith(OPENROUTER_BASE_URL)


def test_the_openrouter_key_is_never_sent_to_anthropic(openrouter, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    client = build_client()
    assert OR_KEY not in json.dumps(dict(client.auth_headers))
    assert "api.anthropic.com" in str(client.base_url)


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_choosing_openrouter_without_its_key_is_a_config_error(monkeypatch, blank):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    if blank is not None:
        monkeypatch.setenv("OPENROUTER_API_KEY", blank)
    with pytest.raises(ConfigError, match="OPENROUTER_API_KEY"):
        build_client()


# ---------------------------------------------------------------- what /health may say
def test_status_for_a_configured_openrouter_setup(openrouter):
    assert provider_status() == {"provider": "openrouter", "model": OR_MODEL, "configured": True}


def test_status_for_a_configured_anthropic_setup():
    assert provider_status() == {"provider": "anthropic", "model": "test-model-from-env",
                                 "configured": True}


def test_status_reports_problems_instead_of_raising(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", OR_KEY)                 # but no OPENROUTER_MODEL
    assert provider_status() == {"provider": "openrouter", "model": None, "configured": False}
    monkeypatch.setenv("LLM_PROVIDER", "some-other-vendor")
    assert provider_status() == {"provider": None, "model": None, "configured": False}


def test_status_never_contains_a_key(openrouter, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "SECRET-ANTHROPIC-KEY")
    dumped = json.dumps(provider_status())
    assert OR_KEY not in dumped
    assert "SECRET-ANTHROPIC-KEY" not in dumped
