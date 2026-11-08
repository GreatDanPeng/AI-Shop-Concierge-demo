"""Test helpers: a fake Anthropic client and content-block builders. No network, no real key.

The assistant loop only reads a few attributes of the SDK objects (type, text, id, name,
input, stop_reason, content), so plain SimpleNamespace objects are enough to stand in.
"""
from types import SimpleNamespace


def text_block(text):
    return SimpleNamespace(type="text", text=text)


def thinking_block(text="private reasoning"):
    return SimpleNamespace(type="thinking", thinking=text, signature="sig")


def tool_use_block(name, tool_input, id="tu_1"):
    return SimpleNamespace(type="tool_use", id=id, name=name, input=tool_input)


def response(*blocks, stop_reason):
    return SimpleNamespace(content=list(blocks), stop_reason=stop_reason,
                           usage=SimpleNamespace(input_tokens=1, output_tokens=1))


def end_turn(text):
    """A final answer."""
    return response(text_block(text), stop_reason="end_turn")


def tool_turn(*tool_blocks):
    """The model asks for one or more tools."""
    return response(*tool_blocks, stop_reason="tool_use")


class FakeMessages:
    def __init__(self, script, loop_last):
        self._script = list(script)
        self._loop_last = loop_last
        self.calls = []

    def create(self, **kwargs):
        # Snapshot the message list: the loop keeps appending to the same list, and we want
        # to see what each request contained when it was sent (the items stay the same objects).
        self.calls.append({**kwargs, "messages": list(kwargs.get("messages", []))})
        if not self._script:
            raise AssertionError("FakeClient: the loop asked for more responses than were scripted")
        item = self._script[0] if (self._loop_last and len(self._script) == 1) else self._script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class FakeClient:
    """Plays back scripted responses (or raises scripted exceptions), one per API call.

    loop_last=True repeats the final item forever, to simulate a model that never stops.
    """

    def __init__(self, *script, loop_last=False):
        self.messages = FakeMessages(script, loop_last)

    @property
    def calls(self):
        return self.messages.calls


class DispatchSpy:
    """Wraps the real dispatch(): records every call, then runs the real thing."""

    def __init__(self, real):
        self._real = real
        self.calls = []

    def __call__(self, name, args, **kwargs):
        self.calls.append({"name": name, "args": args, "kwargs": kwargs})
        return self._real(name, args, **kwargs)
