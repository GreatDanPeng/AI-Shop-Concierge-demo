"""The eval checks that look at HOW the assistant answered, not only at its words (written before them).

check_answer(answer, question) keeps working exactly as before. Three optional question keys are new:
  must_call_tool / must_not_call_tool : names of tools the assistant must / must not have called
  links: "server_only"                : every markdown link in the answer must be one the server offered
  min_links                           : at least this many links
"""
import pytest

from evals.checks import check_answer, find_links

COBALT = "[Cobalt Shoes: 4% cash back](#/store/s4)"
FJORD = "[Fjordline Outdoors: 30% off](#/store/s1)"
OFFERED = {COBALT, FJORD}


# ---------------------------------------------------------------- nothing changes for the old two-argument call
def test_the_old_call_and_its_results_are_unchanged():
    q = {"must_include": ["30%", "as of"], "must_not_include": ["90%"]}
    assert check_answer("30% off, as of Nov 6", q) == []
    assert check_answer("90% off!", q) == ["missing: 30%", "missing: as of", "forbidden: 90%"]


def test_new_keys_are_ignored_when_the_extra_information_is_not_given_and_the_keys_are_absent():
    assert check_answer("anything", {}) == []
    assert check_answer("anything", {"must_include": []}, tool_names=["x"], allowed_links={COBALT}) == []


# ---------------------------------------------------------------- tool calls
def test_a_required_tool_that_was_called_passes():
    q = {"must_call_tool": ["best_combination"]}
    assert check_answer("ok", q, tool_names=["get_eligible_offers", "best_combination"]) == []


def test_a_required_tool_that_was_not_called_is_a_problem():
    q = {"must_call_tool": ["best_combination", "list_all_eligible_offers"]}
    assert check_answer("ok", q, tool_names=["best_combination"]) == ["tool not called: list_all_eligible_offers"]


def test_a_forbidden_tool_that_was_called_is_a_problem():
    q = {"must_not_call_tool": ["list_store_offers"]}
    assert check_answer("ok", q, tool_names=["list_store_offers"]) == ["forbidden tool call: list_store_offers"]
    assert check_answer("ok", q, tool_names=["best_combination"]) == []


@pytest.mark.parametrize("key", ["must_call_tool", "must_not_call_tool"])
def test_asking_for_a_tool_check_without_the_tool_list_is_a_problem_not_a_silent_pass(key):
    assert check_answer("ok", {key: ["x"]}) == ["tool calls were not recorded"]


def test_an_empty_tool_list_is_a_real_answer_not_missing_information():
    assert check_answer("ok", {"must_call_tool": ["x"]}, tool_names=[]) == ["tool not called: x"]
    assert check_answer("ok", {"must_not_call_tool": ["x"]}, tool_names=[]) == []


# ---------------------------------------------------------------- links
def test_find_links_returns_each_markdown_link_in_order():
    text = f"Try {COBALT} and {FJORD}, or [plain](https://evil.example) but not (this)[x] or [a](b c)."
    assert find_links(text) == [COBALT, FJORD, "[plain](https://evil.example)"]


def test_links_the_server_offered_pass():
    q = {"links": "server_only"}
    assert check_answer(f"{COBALT} and {FJORD}", q, allowed_links=OFFERED) == []
    assert check_answer("no links at all", q, allowed_links=OFFERED) == []


@pytest.mark.parametrize("bad", [
    "[Cobalt Shoes: 25% off](#/store/s4)",                  # a label the server never wrote
    "[Cobalt Shoes: 4% cash back](#/store/s1)",             # the right label, the wrong store
    "[Cobalt Shoes: 4% cash back](https://evil.example)",   # an outside address
    "[Cobalt Shoes: 4% cash back](javascript:alert(1))",
    "[Pay now](#/store/s4)",
])
def test_a_link_the_server_did_not_offer_is_a_problem(bad):
    assert check_answer(f"{FJORD} {bad}", {"links": "server_only"}, allowed_links=OFFERED) == [
        f"link not offered by the server: {bad}"]


def test_a_link_check_without_the_offered_set_is_a_problem_not_a_silent_pass():
    assert check_answer(COBALT, {"links": "server_only"}) == ["offered links were not provided"]


def test_min_links_counts_links_and_does_not_need_the_offered_set():
    q = {"min_links": 2}
    assert check_answer(f"{COBALT} {FJORD}", q) == []
    assert check_answer(COBALT, q) == ["links: 1, at least 2 expected"]
    assert check_answer("none", {"min_links": 1}) == ["links: 0, at least 1 expected"]


def test_unknown_link_mode_is_refused_loudly():
    with pytest.raises(ValueError, match="links"):
        check_answer(COBALT, {"links": "whatever"}, allowed_links=OFFERED)


def test_all_checks_report_together_in_a_stable_order():
    q = {"must_include": ["x"], "must_not_include": ["y"], "must_call_tool": ["t"],
         "must_not_call_tool": ["u"], "links": "server_only", "min_links": 3}
    problems = check_answer("y [a](#/store/s9)", q, tool_names=["u"], allowed_links=OFFERED)
    assert problems == ["missing: x", "forbidden: y", "tool not called: t", "forbidden tool call: u",
                        "link not offered by the server: [a](#/store/s9)", "links: 1, at least 3 expected"]
