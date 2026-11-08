"""The HTTP API: identity matching, the real /chat, startup, and serving the built web app.

TestClient only: no network, no real key. The assistant itself is replaced by a spy here; its own
behaviour is covered in test_assistant*.py.
"""
import json
import logging

import pytest
from fastapi.testclient import TestClient

from app import server
from app.assistant import AssistantResult, AssistantUnavailable, ConfigError, UnknownStoreError

CLIENT_SENTINEL = object()


class ChatSpy:
    """Stands in for run_assistant: records the call, then returns a result or raises an error."""

    def __init__(self, result=None, error=None):
        self.result = result or AssistantResult("hello there", [{"name": "x", "input": {}, "error": None}])
        self.error = error
        self.calls = []

    def __call__(self, message, member_id, store_id, *, client=None, **kwargs):
        self.calls.append({"message": message, "member_id": member_id, "store_id": store_id,
                           "client": client})
        if self.error is not None:
            raise self.error
        return self.result


@pytest.fixture
def client():
    return TestClient(server.app)


@pytest.fixture
def chat_spy(monkeypatch):
    spy = ChatSpy()
    monkeypatch.setattr(server, "run_assistant", spy)
    monkeypatch.setattr(server, "_client", lambda: CLIENT_SENTINEL)
    return spy


def sign_in(client, member_id):
    assert client.post("/demo/switch-member", json={"member_id": member_id}).status_code == 200
    return client


# ---------------------------------------------------------------- who is asking (always the cookie)
@pytest.mark.parametrize("method, path, kwargs", [
    ("get", "/me", {}),
    ("get", "/discounts", {}),
    ("get", "/estimate?store_id=s1&cart_cents=20000", {}),
    ("post", "/chat", {"json": {"message": "hi"}}),
])
def test_nothing_personal_is_served_without_signing_in(client, method, path, kwargs):
    r = getattr(client, method)(path, **kwargs)
    assert r.status_code == 401
    assert r.json() == {"detail": "not_signed_in"}


def test_a_tampered_cookie_is_not_a_login(client):
    client.cookies.set("member_id", "m_nobody")
    assert client.get("/me").status_code == 401


def test_signing_in_sets_an_http_only_same_site_cookie(client):
    r = client.post("/demo/switch-member", json={"member_id": "m_nurse"})
    cookie = r.headers["set-cookie"].lower()
    assert "member_id=m_nurse" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_switching_to_an_unknown_member_is_refused(client):
    assert client.post("/demo/switch-member", json={"member_id": "nobody"}).status_code == 404


def test_the_member_never_comes_from_the_query_string(client):
    sign_in(client, "m_nurse")
    baseline = client.get("/discounts").json()
    assert client.get("/discounts?member_id=m_student&member=m_student").json() == baseline
    assert client.get("/me?member_id=m_student").json()["member_id"] == "m_nurse"


# ---------------------------------------------------------------- /me, /discounts, /estimate, /demo/members
def test_me_is_the_signed_in_members_own_identity_without_an_email(client):
    sign_in(client, "m_student")
    body = client.get("/me").json()
    assert body["member_id"] == "m_student"
    assert body["verifications"][0]["status"] == "expired"
    assert "email" not in json.dumps(body)
    assert "example.invalid" not in json.dumps(body)


def test_discounts_lists_every_store_with_reasons_for_the_signed_in_member(client):
    sign_in(client, "m_unverified")
    body = client.get("/discounts").json()
    assert body["as_of"] == "2026-11-06"
    assert [s["store_id"] for s in body["stores"]] == ["s1", "s2", "s3", "s4", "s5", "s6"]
    s1 = {o["offer_id"]: o for o in body["stores"][0]["offers"]}
    assert s1["o1"]["reasons"] == ["NOT_VERIFIED"]
    assert s1["o2"]["eligible"] is True


def test_discounts_holds_no_terms_text_and_no_personal_data(client):
    sign_in(client, "m_nurse")
    dumped = client.get("/discounts").text
    assert "IGNORE ALL PREVIOUS" not in dumped
    assert "terms" not in dumped
    assert "example.invalid" not in dumped


def test_estimate_comes_from_the_engine(client):
    sign_in(client, "m_nurse")
    r = client.get("/estimate", params={"store_id": "s1", "cart_cents": 20000})
    assert r.status_code == 200
    body = r.json()
    assert (body["you_pay_cents"], body["cash_back_cents"], body["total_savings_cents"]) == (14000, 490, 6490)
    assert body["as_of"] == "2026-11-06"


def test_estimate_for_the_signed_in_member_not_for_anyone_else(client):
    sign_in(client, "m_military")
    body = client.get("/estimate", params={"store_id": "s1", "cart_cents": 30000}).json()
    assert body["group_discount"] is None
    assert body["cash_back_cents"] == 1050


def test_estimate_rejects_an_unknown_store(client):
    sign_in(client, "m_nurse")
    r = client.get("/estimate", params={"store_id": "s999", "cart_cents": 20000})
    assert r.status_code == 400
    assert r.json() == {"detail": "unknown_store"}


@pytest.mark.parametrize("cart", ["0", "-5", "abc", "1.5", "", "100000001"])
def test_estimate_rejects_a_bad_cart_total(client, cart):
    sign_in(client, "m_nurse")
    assert client.get("/estimate", params={"store_id": "s1", "cart_cents": cart}).status_code == 422


def test_estimate_requires_both_parameters(client):
    sign_in(client, "m_nurse")
    assert client.get("/estimate?store_id=s1").status_code == 422
    assert client.get("/estimate?cart_cents=100").status_code == 422


def test_demo_members_lists_the_five_profiles_without_emails(client):
    body = client.get("/demo/members").json()
    assert [m["id"] for m in body] == ["m_nurse", "m_student", "m_unverified", "m_military", "m_teacher"]
    sam = next(m for m in body if m["id"] == "m_student")
    assert sam["display_name"] == "Sam"
    assert sam["verifications"] == [{"group": "student", "status": "expired"}]
    assert next(m for m in body if m["id"] == "m_unverified")["verifications"] == []
    assert "example.invalid" not in json.dumps(body)


# ---------------------------------------------------------------- /health
def test_health_reports_the_assistant_setup_but_never_a_key(client, monkeypatch):
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "LLM_PROVIDER"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "SECRET-OR-KEY-123")
    monkeypatch.setenv("OPENROUTER_MODEL", "some/model-id")
    r = client.get("/health")                              # no sign-in needed
    assert r.json() == {"ok": True, "assistant": {"provider": "openrouter", "model": "some/model-id",
                                                  "configured": True}}
    assert "SECRET-OR-KEY-123" not in r.text


def test_health_says_when_the_assistant_is_not_configured(client, monkeypatch):
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENROUTER_API_KEY",
                 "OPENROUTER_MODEL", "ANTHROPIC_MODEL", "LLM_PROVIDER"):
        monkeypatch.delenv(name, raising=False)
    assert client.get("/health").json()["assistant"]["configured"] is False


# ---------------------------------------------------------------- /chat
def test_chat_returns_only_the_reply(client, chat_spy):
    sign_in(client, "m_nurse")
    r = client.post("/chat", json={"message": "  What can I get?  ", "store_id": "s1"})
    assert r.status_code == 200
    assert r.json() == {"reply": "hello there"}              # no tool_calls, no status
    [call] = chat_spy.calls
    assert call["message"] == "What can I get?"             # trimmed
    assert call["member_id"] == "m_nurse"                   # from the cookie
    assert call["store_id"] == "s1"
    assert call["client"] is CLIENT_SENTINEL                # the shared client, not one per request


def test_chat_works_without_a_store(client, chat_spy):
    sign_in(client, "m_nurse")
    assert client.post("/chat", json={"message": "hi"}).status_code == 200
    assert chat_spy.calls[0]["store_id"] is None


@pytest.mark.parametrize("error, status, detail", [
    (UnknownStoreError("unknown store"), 400, "unknown_store"),
    (ConfigError("OPENROUTER_MODEL is not set"), 503, "assistant_not_configured"),
    (AssistantUnavailable("the model API call failed"), 502, "assistant_unavailable"),
])
def test_assistant_errors_become_clear_http_errors(client, monkeypatch, error, status, detail):
    monkeypatch.setattr(server, "run_assistant", ChatSpy(error=error))
    monkeypatch.setattr(server, "_client", lambda: CLIENT_SENTINEL)
    sign_in(client, "m_nurse")
    r = client.post("/chat", json={"message": "hi"})
    assert (r.status_code, r.json()) == (status, {"detail": detail})
    assert "OPENROUTER_MODEL" not in r.text                 # internals are not shown to the browser


def test_a_missing_key_when_building_the_client_is_a_503(client, monkeypatch):
    def no_key():
        raise ConfigError("OPENROUTER_API_KEY is not set")
    monkeypatch.setattr(server, "_client", no_key)
    monkeypatch.setattr(server, "run_assistant", ChatSpy())
    sign_in(client, "m_nurse")
    r = client.post("/chat", json={"message": "hi"})
    assert (r.status_code, r.json()) == (503, {"detail": "assistant_not_configured"})


@pytest.mark.parametrize("body", [
    {"message": ""}, {"message": "   "}, {"message": "x" * 2001}, {"message": "hi", "store_id": "s" * 65},
    {}, {"message": 5},
    {"message": "hi", "member_id": "m_student"},            # the body can never choose the member
])
def test_bad_chat_requests_are_rejected_before_the_model_is_involved(client, chat_spy, body):
    sign_in(client, "m_nurse")
    assert client.post("/chat", json=body).status_code == 422
    assert chat_spy.calls == []


def test_the_longest_allowed_message_is_accepted(client, chat_spy):
    sign_in(client, "m_nurse")
    assert client.post("/chat", json={"message": "x" * 2000}).status_code == 200


def test_chat_does_not_log_the_message(client, chat_spy, caplog):
    caplog.set_level(logging.DEBUG)
    sign_in(client, "m_nurse")
    client.post("/chat", json={"message": "MARKER-PRIVATE-QUESTION-42"})
    assert "MARKER-PRIVATE-QUESTION-42" not in caplog.text


def test_the_api_client_is_built_once_and_reused(monkeypatch):
    built = []
    monkeypatch.setattr(server, "build_client", lambda: built.append(1) or object())
    server._client.cache_clear()
    try:
        assert server._client() is server._client()
        assert len(built) == 1
    finally:
        server._client.cache_clear()


# ---------------------------------------------------------------- startup loads .env, import does not
def test_the_env_file_is_loaded_when_the_server_starts_not_on_import(monkeypatch):
    loaded = []
    monkeypatch.setattr(server, "load_env_file", lambda *a, **k: loaded.append(1) or [])
    TestClient(server.app).get("/health")                   # no context manager: no startup
    assert loaded == []
    with TestClient(server.app) as started:
        started.get("/health")
    assert loaded == [1]


# ---------------------------------------------------------------- serving the built web app
@pytest.fixture
def dist(tmp_path):
    (tmp_path / ".env").write_text("OPENROUTER_API_KEY=MARKER-SECRET-IN-PARENT\n", encoding="utf-8")
    web = tmp_path / "dist"
    (web / "assets").mkdir(parents=True)
    (web / "index.html").write_text("<!doctype html><title>Demo Shop</title>", encoding="utf-8")
    (web / "widget.js").write_text("console.log('widget')", encoding="utf-8")
    return web


def test_the_built_page_is_served_at_the_root_and_api_routes_still_win(dist):
    web_client = TestClient(server.create_app(web_dist=dist))
    assert "Demo Shop" in web_client.get("/").text
    assert web_client.get("/widget.js").text == "console.log('widget')"
    assert web_client.get("/health").json()["ok"] is True       # API, not the static mount
    assert web_client.post("/chat", json={"message": "hi"}).status_code == 401
    assert web_client.get("/me").status_code == 401


@pytest.mark.parametrize("path", ["/.env", "/../.env", "/%2e%2e/.env", "/..%2f.env", "/assets/../../.env",
                                  "/%2e%2e%2f.env"])
def test_secrets_next_to_the_build_can_never_be_served(dist, path):
    web_client = TestClient(server.create_app(web_dist=dist))
    r = web_client.get(path)
    assert "MARKER-SECRET-IN-PARENT" not in r.text
    assert r.status_code in (404, 400)


def test_without_a_build_the_root_explains_what_to_run(tmp_path):
    web_client = TestClient(server.create_app(web_dist=tmp_path / "missing"))
    r = web_client.get("/")
    assert r.status_code == 200
    assert "npm run build" in r.text
    assert web_client.get("/health").json()["ok"] is True
