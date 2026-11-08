"""Edge cases found by probing the running system (not by reading the code).

1. A misbehaving model API (HTTP errors, HTML instead of JSON, malformed bodies) must never become an
   unhandled exception (an HTTP 500) and must never leak upstream text.
2. The SDK's own DEBUG logs contain the full request (the member's message and tool results), so
   they must never be emitted, even if someone turns on debug logging.
3. A damaged .env must not stop the server from starting: matching works without the model.

Real SDK over a mock HTTP transport. No network and no real keys.
"""
import logging
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import anthropic
import httpx2
import pytest
from fastapi.testclient import TestClient

from app import env as env_module
from app import server
from app.assistant import FAILURE_MESSAGE, AssistantUnavailable, run_assistant
from app.env import load_env_file
from tests.fakes import FakeClient

pytestmark = pytest.mark.usefixtures("configured_env")

ROOT = Path(__file__).resolve().parent.parent
LEAK = "MARKER-UPSTREAM-LEAK-31c"
MSG = "MARKER-USER-MESSAGE-5d2"
GOOD = {"id": "m", "type": "message", "role": "assistant", "model": "m", "stop_reason": "end_turn",
        "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1},
        "content": [{"type": "text", "text": "ok"}]}


def sdk_client(handler):
    return anthropic.Anthropic(http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
                               max_retries=0)


def fails(request):
    raise AssertionError("not used")


# ---------------------------------------------------------------- 1. a misbehaving model API
BROKEN = {
    "401 key rejected": lambda r: httpx2.Response(401, json={"type": "error", "error": {
        "type": "authentication_error", "message": f"Invalid key {LEAK}"}}),
    "402 out of credits": lambda r: httpx2.Response(402, json={"error": {"code": 402, "message": LEAK}}),
    "429 rate limited": lambda r: httpx2.Response(429, json={"error": {"message": LEAK}},
                                                  headers={"retry-after": "1"}),
    "500 server error": lambda r: httpx2.Response(500, json={"error": {"message": LEAK}}),
    "502 html from a proxy": lambda r: httpx2.Response(502, text=f"<html>{LEAK}</html>"),
    "200 but html instead of json": lambda r: httpx2.Response(200, text=f"<html>{LEAK}</html>"),
    "200 with content null": lambda r: httpx2.Response(200, json={**GOOD, "content": None}),
    "200 with an empty json object": lambda r: httpx2.Response(200, json={}),
    "connection refused": lambda r: (_ for _ in ()).throw(httpx2.ConnectError(LEAK, request=r)),
    "read timeout": lambda r: (_ for _ in ()).throw(httpx2.ReadTimeout(LEAK, request=r)),
}


@pytest.mark.parametrize("handler", BROKEN.values(), ids=BROKEN.keys())
def test_a_broken_model_api_becomes_assistant_unavailable_and_leaks_nothing(handler, caplog):
    caplog.set_level(logging.DEBUG)
    with pytest.raises(AssistantUnavailable) as caught:
        run_assistant("hello", "m_nurse", "s1", client=sdk_client(handler))
    assert LEAK not in str(caught.value)
    assert LEAK not in caplog.text


MALFORMED_BUT_PARSED = {
    "unknown block type": {**GOOD, "content": [{"type": "weird", "x": 1}]},
    "stop_reason null": {**GOOD, "stop_reason": None},
    "text block with text null": {**GOOD, "content": [{"type": "text", "text": None}]},
}


@pytest.mark.parametrize("body", MALFORMED_BUT_PARSED.values(), ids=MALFORMED_BUT_PARSED.keys())
def test_an_odd_but_parseable_answer_gives_the_failure_message(body):
    result = run_assistant("hello", "m_nurse", "s1",
                           client=sdk_client(lambda r: httpx2.Response(200, json=body)))
    assert result.reply == FAILURE_MESSAGE
    assert result.status == "model_stopped"


@pytest.mark.parametrize("bad_response", [
    "<html>not a message</html>",                              # the SDK hands back plain text
    SimpleNamespace(stop_reason="end_turn", content=None),
    SimpleNamespace(stop_reason="end_turn"),                   # no content attribute at all
    SimpleNamespace(content=[]),                               # no stop_reason attribute at all
], ids=["plain text", "content None", "no content", "no stop_reason"])
def test_a_response_of_the_wrong_shape_is_an_unavailable_assistant_not_a_crash(bad_response):
    with pytest.raises(AssistantUnavailable):
        run_assistant("hello", "m_nurse", "s1", client=FakeClient(bad_response))


# ---------------------------------------------------------------- 2. the SDK's debug logs
def ok_handler(request):
    return httpx2.Response(200, json={**GOOD, "content": [{"type": "text", "text": f"reply {LEAK}"}]})


def test_debug_logging_never_writes_the_message_or_the_reply(caplog):
    caplog.set_level(logging.DEBUG)                            # the root logger at its noisiest
    run_assistant(MSG, "m_nurse", "s1", client=sdk_client(ok_handler))
    assert MSG not in caplog.text
    assert LEAK not in caplog.text


def test_the_sdks_own_debug_switch_cannot_make_it_log_the_message():
    code = (
        "import sys; sys.path.insert(0, %r)\n"
        "import anthropic, httpx2\n"
        "from app.assistant import run_assistant\n"
        "def h(request):\n"
        "    return httpx2.Response(200, json=%r)\n"
        "client = anthropic.Anthropic(http_client=httpx2.Client(transport=httpx2.MockTransport(h)), max_retries=0)\n"
        "run_assistant(%r, 'm_nurse', 's1', client=client)\n"
        % (str(ROOT), GOOD, MSG)
    )
    env = {**os.environ, "ANTHROPIC_LOG": "debug", "ANTHROPIC_API_KEY": "test-key-not-real",
           "ANTHROPIC_MODEL": "probe-model"}
    done = subprocess.run([sys.executable, "-I", "-c", code], env=env, cwd=ROOT,
                          capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    assert MSG not in done.stdout + done.stderr


# ---------------------------------------------------------------- 3. a damaged .env
def bad_utf8(path):
    path.write_bytes(b"OPENROUTER_API_KEY=MARKER-ENV-SECRET\xff\xfe\nX=1\n")


def a_directory(path):
    path.mkdir()


def no_permission(path):
    path.write_text("OPENROUTER_API_KEY=MARKER-ENV-SECRET\n", encoding="utf-8")
    path.chmod(0)


@pytest.mark.parametrize("make", [bad_utf8, a_directory, no_permission],
                         ids=["invalid utf-8", "a directory", "no read permission"])
def test_an_unreadable_env_file_is_skipped_with_a_warning_not_a_crash(tmp_path, caplog, make):
    if make is no_permission and os.geteuid() == 0:
        pytest.skip("root can read everything")
    caplog.set_level(logging.DEBUG)
    path = tmp_path / ".env"
    make(path)
    environ = {"KEEP": "1"}
    try:
        assert load_env_file(path, environ=environ) == []
    finally:
        if path.is_file():
            path.chmod(0o600)
    assert environ == {"KEEP": "1"}
    assert any(r.levelno == logging.WARNING for r in caplog.records)
    assert "MARKER-ENV-SECRET" not in caplog.text


def test_the_server_still_starts_and_matches_discounts_with_a_damaged_env_file(tmp_path, monkeypatch):
    broken = tmp_path / ".env"
    broken.write_bytes(b"\xff\xfe not text \x00")
    monkeypatch.setattr(env_module, "DEFAULT_ENV_PATH", broken)
    with TestClient(server.app) as started:                    # startup runs load_env_file()
        assert started.post("/demo/switch-member", json={"member_id": "m_nurse"}).status_code == 200
        assert started.get("/discounts").status_code == 200
        assert started.get("/health").json()["assistant"]["configured"] is True   # from the fixture env


# ---------------------------------------------------------------- 4. odd amounts and languages (found live)
def test_the_tool_and_the_web_api_share_one_upper_limit_for_a_cart():
    from app import tools
    assert tools.MAX_CART_CENTS == server.MAX_CART_CENTS == 100_000_000      # $1,000,000.00


def test_a_cart_above_the_limit_is_refused_by_the_tool_but_the_limit_itself_is_fine():
    from app.tools import MAX_CART_CENTS, dispatch
    over = dispatch("best_combination", {"store_id": "s1", "cart_cents": MAX_CART_CENTS + 1},
                    member_id="m_nurse")
    assert over == {"error": "bad_arguments"}
    at_limit = dispatch("best_combination", {"store_id": "s1", "cart_cents": MAX_CART_CENTS},
                        member_id="m_nurse")
    assert "error" not in at_limit
    assert at_limit["dollars"]["cart"] == "$1,000,000.00"


def test_an_absurdly_long_integer_is_refused_quickly():
    from app.tools import dispatch
    assert dispatch("best_combination", {"store_id": "s1", "cart_cents": 10 ** 5000},
                    member_id="m_nurse") == {"error": "bad_arguments"}


def test_the_prompt_asks_for_the_cart_total_instead_of_guessing_or_adding():
    from app.assistant import build_system_prompt
    prompt = build_system_prompt(None).lower()
    assert "zero, negative or unclear" in prompt
    assert "several amounts" in prompt
    assert "cart total" in prompt


def test_the_prompt_asks_for_answers_in_the_members_language():
    from app.assistant import build_system_prompt
    assert "language the member wrote in" in build_system_prompt(None)
