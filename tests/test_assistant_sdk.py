"""The assistant loop through the REAL anthropic SDK, over a mock HTTP transport.

No network and no real key. The fake client in test_assistant.py cannot show that the SDK
accepts what the loop sends (replayed thinking and tool_use blocks, tool_result blocks) or
which URL and auth header a custom base URL produces; this does. The second test is the
offline half of the cheap-model setup (an Anthropic-compatible endpoint such as OpenRouter's).
"""
import json

import anthropic
import httpx2
import pytest

from app.assistant import run_assistant

pytestmark = pytest.mark.usefixtures("configured_env")


def message_json(content, stop_reason):
    return {"id": "msg_1", "type": "message", "role": "assistant", "model": "m", "content": content,
            "stop_reason": stop_reason, "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 5}}


def sdk_client_and_requests():
    """A real SDK client whose HTTP layer is a script: one tool call, then a final answer."""
    requests = []

    def handler(request):
        requests.append({"url": str(request.url), "headers": request.headers,
                         "body": json.loads(request.content)})
        if len(requests) == 1:
            return httpx2.Response(200, json=message_json([
                {"type": "thinking", "thinking": "need the cart math", "signature": "sig123"},
                {"type": "text", "text": "Let me check."},
                {"type": "tool_use", "id": "toolu_1", "name": "best_combination",
                 "input": {"store_id": "s1", "cart_cents": 20000}}], "tool_use"))
        return httpx2.Response(200, json=message_json(
            [{"type": "text", "text": "You pay $140.00 and get $4.90 back."}], "end_turn"))

    client = anthropic.Anthropic(http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
                                 max_retries=0)
    return client, requests


def test_the_real_sdk_accepts_the_replayed_turn_and_the_tool_result():
    client, requests = sdk_client_and_requests()
    result = run_assistant("I'm buying $200 of gear. What do I pay?", "m_nurse", "s1", client=client)

    assert result.reply == "You pay $140.00 and get $4.90 back."
    assert result.status == "ok"
    assert [c["name"] for c in result.tool_calls] == ["best_combination"]

    first, second = requests
    assert sorted(first["body"]) == ["max_tokens", "messages", "model", "system", "tools"]
    assert "list_store_offers" in [t["name"] for t in first["body"]["tools"]]
    assert [m["role"] for m in second["body"]["messages"]] == ["user", "assistant", "user"]
    replayed = second["body"]["messages"][1]["content"]
    assert [b["type"] for b in replayed] == ["thinking", "text", "tool_use"]   # nothing dropped
    tool_result = second["body"]["messages"][2]["content"][0]
    assert tool_result["type"] == "tool_result"
    assert tool_result["tool_use_id"] == "toolu_1"
    assert "is_error" not in tool_result
    numbers = json.loads(tool_result["content"])
    assert (numbers["you_pay_cents"], numbers["cash_back_cents"]) == (14000, 490)


def test_an_anthropic_compatible_endpoint_is_reached_with_the_env_settings(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "or-test-token-not-real")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://openrouter.ai/api")
    monkeypatch.setenv("ANTHROPIC_MODEL", "deepseek/deepseek-v4.1-flash-1017")
    client, requests = sdk_client_and_requests()   # built after the env is set, like production
    run_assistant("What discounts can I get here?", "m_nurse", "s1", client=client)

    first = requests[0]
    assert first["url"] == "https://openrouter.ai/api/v1/messages"
    assert first["headers"]["authorization"] == "Bearer or-test-token-not-real"
    assert "x-api-key" not in first["headers"]
    assert first["body"]["model"] == "deepseek/deepseek-v4.1-flash-1017"
