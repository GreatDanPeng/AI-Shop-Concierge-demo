"""Simple, explainable checks for an assistant answer.

These are heuristics, not a proof of quality: case-insensitive substring checks on the words, plus checks
on what the assistant DID (which tools it called) and on the links in its answer. Say so wherever a pass
rate is quoted. A failing check is not automatically the model's fault: read the answer first (a check
that is too strict looks exactly like a model that is wrong).

A question may carry, besides must_include / must_not_include:
  must_call_tool, must_not_call_tool : lists of tool names
  links: "server_only"               : every markdown link in the answer is one the server offered
  min_links                          : at least this many links
"""
import re

# [label](address): the label holds no bracket, parenthesis or line break; the address no space. The address
# may hold one level of parentheses, so a suspicious one such as javascript:alert(1) is still found (the page
# itself would show it as plain text, but an eval should say it was written).
_LINK = re.compile(r"\[[^\[\]()\n]+\]\((?:[^()\s]|\([^()\s]*\))*\)")
LINK_MODES = ("server_only",)


def find_links(answer: str) -> list[str]:
    """Every markdown link in the answer, as written, in order."""
    return _LINK.findall(answer)


def _word_problems(answer: str, question: dict) -> list[str]:
    low = answer.lower()
    problems = [f"missing: {text}" for text in question.get("must_include", []) if text.lower() not in low]
    problems += [f"forbidden: {text}" for text in question.get("must_not_include", []) if text.lower() in low]
    return problems


def _tool_problems(question: dict, tool_names) -> list[str]:
    must, must_not = question.get("must_call_tool", []), question.get("must_not_call_tool", [])
    if not must and not must_not:
        return []
    if tool_names is None:
        return ["tool calls were not recorded"]
    problems = [f"tool not called: {name}" for name in must if name not in tool_names]
    problems += [f"forbidden tool call: {name}" for name in must_not if name in tool_names]
    return problems


def _link_problems(answer: str, question: dict, allowed_links) -> list[str]:
    mode = question.get("links")
    if mode is not None and mode not in LINK_MODES:
        raise ValueError(f"links must be one of {LINK_MODES}, not {mode!r}")
    links = find_links(answer)
    problems = []
    if mode == "server_only":
        if allowed_links is None:
            problems.append("offered links were not provided")
        else:
            problems += [f"link not offered by the server: {link}" for link in links if link not in allowed_links]
    minimum = question.get("min_links")
    if minimum is not None and len(links) < minimum:
        problems.append(f"links: {len(links)}, at least {minimum} expected")
    return problems


def check_answer(answer: str, question: dict, tool_names=None, allowed_links=None) -> list[str]:
    """Return a list of problems; an empty list means the answer passed.

    tool_names: the tools the assistant called, in order (needed only for must_call_tool and
    must_not_call_tool). allowed_links: the links the server offered this member (needed only for
    links: "server_only").
    """
    return (_word_problems(answer, question) + _tool_problems(question, tool_names)
            + _link_problems(answer, question, allowed_links))
