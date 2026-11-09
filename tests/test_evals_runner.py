"""The eval runner (written before it): asks every question, counts passes, labels the result.

Everything here uses a fake model or a fake ask function: no network, no real key, and the repo's own
.env is never read (main() takes the loader as an argument).
"""
import json
import os
import re
from datetime import date

import pytest

from app import assistant
from app.assistant import AssistantUnavailable, ConfigError
from app.catalog import BRANDS_VARIABLE
from evals.run_evals import (Answer, ask, build_report, main, prompt_fingerprint, run_questions,
                             summarise, write_report)
from tests.fakes import FakeClient, end_turn, tool_turn, tool_use_block

pytestmark = pytest.mark.usefixtures("configured_env")

Q = {"id": "t1", "member_id": "m_teacher", "store_id": "s1", "question": "What can I get?"}
# With the brand catalog on, the original stores are unknown, so a brand question names no store.
BRANDS_Q = {**Q, "store_id": None, "catalog": "brands"}


def sent_tool_result(client):
    [block] = client.calls[1]["messages"][-1]["content"]
    return json.loads(block["content"])


def answer(text="ok", tools=(), status="ok", links=()):
    return Answer(text, list(tools), status, frozenset(links))


# ---------------------------------------------------------------- ask(): one real question through the loop
def test_ask_gives_the_assistant_the_questions_own_member_and_store():
    client = FakeClient(tool_turn(tool_use_block("get_eligible_offers", {"store_id": "s1"})), end_turn("done"))
    result = ask(Q, client)
    assert (result.text, result.tool_names, result.status) == ("done", ["get_eligible_offers"], "ok")
    assert [o["offer_id"] for o in sent_tool_result(client)["offers"]] == ["o1", "o2"]   # Morgan at s1
    assert client.calls[0]["messages"][0]["content"] == Q["question"]
    assert "currently viewing s1" in client.calls[0]["system"]


@pytest.mark.parametrize("question", [
    {**Q, "store_id": None},
    {k: v for k, v in Q.items() if k != "store_id"},
])
def test_a_question_with_no_store_is_asked_with_no_store(question):
    client = FakeClient(end_turn("done"))
    ask(question, client)
    assert "currently viewing" not in client.calls[0]["system"]


def test_the_catalog_is_the_original_six_stores_unless_the_question_asks_for_the_brands():
    brands = {**Q, "store_id": None, "catalog": "brands"}
    call = tool_turn(tool_use_block("list_all_eligible_offers", {}))
    original_client, brand_client = FakeClient(call, end_turn("a")), FakeClient(call, end_turn("b"))
    ask({**Q, "store_id": None}, original_client)
    ask(brands, brand_client)
    original_ids = [o["offer_id"] for o in sent_tool_result(original_client)["offers"]]
    brand_ids = [o["offer_id"] for o in sent_tool_result(brand_client)["offers"]]
    assert "o10" not in original_ids and "o10" in brand_ids      # Apple 20% for teachers


def test_the_catalog_switch_is_put_back_afterwards(monkeypatch):
    ask(BRANDS_Q, FakeClient(end_turn("x")))
    assert os.environ[BRANDS_VARIABLE] == "off"                  # conftest's value, restored
    monkeypatch.delenv(BRANDS_VARIABLE)
    ask(BRANDS_Q, FakeClient(end_turn("x")))
    assert BRANDS_VARIABLE not in os.environ                     # and "unset" is restored as unset


def test_the_switch_is_restored_even_when_the_assistant_fails():
    with pytest.raises(AssistantUnavailable):
        ask(BRANDS_Q, FakeClient(AssistantUnavailable("down")))
    assert os.environ[BRANDS_VARIABLE] == "off"


def test_ask_also_returns_the_links_the_server_offers_this_member():
    nurse = ask({**Q, "member_id": "m_nurse"}, FakeClient(end_turn("x")))
    assert "[Fjordline Outdoors: 30% off](#/store/s1)" in nurse.allowed_links
    morgan_original = ask(Q, FakeClient(end_turn("x")))
    morgan_brands = ask(BRANDS_Q, FakeClient(end_turn("x")))
    assert "[Apple: 20% off](#/store/s7)" in morgan_brands.allowed_links
    assert "[Apple: 20% off](#/store/s7)" not in morgan_original.allowed_links


def test_an_assistant_that_stops_early_is_reported_by_its_status():
    assert ask(Q, FakeClient(end_turn(""))).status == "model_stopped"


# ---------------------------------------------------------------- run_questions
def test_every_question_is_asked_repeat_times_in_order_with_a_full_record():
    questions = [{**Q, "id": "a", "must_include": ["30%"]}, {**Q, "id": "b", "must_include": ["zzz"]}]
    records = run_questions(questions, lambda q: answer("30% off, as of today", ["get_eligible_offers"]), repeat=2)
    assert [(r["id"], r["run"]) for r in records] == [("a", 1), ("a", 2), ("b", 1), ("b", 2)]
    assert [r["passed"] for r in records] == [True, True, False, False]
    first = records[0]
    assert set(first) == {"id", "run", "passed", "problems", "answer", "tools", "error", "catalog"}
    assert first["answer"] == "30% off, as of today" and first["tools"] == ["get_eligible_offers"]
    assert records[2]["problems"] == ["missing: zzz"] and first["catalog"] == "original"


def test_the_tool_and_link_checks_are_applied_with_what_the_assistant_did():
    q = {**Q, "must_call_tool": ["best_combination"], "links": "server_only"}
    [bad] = run_questions([q], lambda _: answer("see [x](#/store/s9)", ["get_eligible_offers"]))
    assert bad["problems"] == ["tool not called: best_combination", "link not offered by the server: [x](#/store/s9)"]
    good_link = "[Fjordline Outdoors: 30% off](#/store/s1)"
    [good] = run_questions([q], lambda _: answer(f"see {good_link}", ["best_combination"], links=[good_link]))
    assert good["passed"] is True


@pytest.mark.parametrize("status", ["max_rounds", "model_stopped"])
def test_an_assistant_that_gives_up_is_a_failed_run_not_a_crash(status):
    [r] = run_questions([Q], lambda _: answer("Sorry, I couldn't finish that.", status=status))
    assert r["passed"] is False and r["error"] is False
    assert r["problems"] == [f"assistant gave up: {status}"]


def test_an_unavailable_model_is_an_error_run_and_the_rest_still_run():
    def flaky(q):
        if q["id"] == "a":
            raise AssistantUnavailable("down")
        return answer("fine")
    records = run_questions([{**Q, "id": "a"}, {**Q, "id": "b"}], flaky)
    assert [(r["id"], r["passed"], r["error"]) for r in records] == [("a", False, True), ("b", True, False)]
    assert records[0]["problems"] == ["assistant unavailable"] and records[0]["answer"] == ""


def test_a_setup_problem_is_not_swallowed():
    def broken(_):
        raise ConfigError("OPENROUTER_API_KEY is not set")
    with pytest.raises(ConfigError):
        run_questions([Q], broken)


def test_repeat_must_be_at_least_one():
    with pytest.raises(ValueError):
        run_questions([Q], lambda _: answer(), repeat=0)


# ---------------------------------------------------------------- summarise
def records_of(*spec):
    return [{"id": i, "run": n, "passed": p, "problems": [] if p else ["missing: x"], "answer": "", "tools": [],
             "error": e, "catalog": "original"} for i, n, p, e in spec]


def test_the_summary_counts_per_question_and_overall_with_integer_percentages():
    s = summarise(records_of(("a", 1, True, False), ("a", 2, True, False), ("a", 3, False, False),
                             ("b", 1, False, True)))
    assert s["per_question"] == {"a": {"passed": 2, "runs": 3}, "b": {"passed": 0, "runs": 1}}
    assert (s["passed"], s["runs"], s["errors"], s["percent"]) == (2, 4, 1, 50)
    assert [(f["id"], f["run"]) for f in s["failures"]] == [("a", 3), ("b", 1)]


@pytest.mark.parametrize("passed, runs, percent", [(1, 3, 33), (2, 3, 67), (3, 3, 100), (0, 3, 0), (1, 8, 13)])
def test_percentages_are_rounded_half_up_with_integers(passed, runs, percent):
    spec = [("a", n, n <= passed, False) for n in range(1, runs + 1)]
    assert summarise(records_of(*spec))["percent"] == percent


def test_an_empty_run_has_no_percentage_and_no_division_by_zero():
    assert summarise([])["percent"] is None


# ---------------------------------------------------------------- labelling
def test_the_prompt_fingerprint_is_short_stable_and_changes_with_the_prompt(monkeypatch):
    first = prompt_fingerprint()
    assert re.fullmatch(r"[0-9a-f]{8}", first) and prompt_fingerprint() == first
    monkeypatch.setattr(assistant, "SYSTEM_RULES", assistant.SYSTEM_RULES + " Extra rule.")
    assert prompt_fingerprint() != first


def test_the_prompt_fingerprint_also_changes_with_the_tools(monkeypatch):
    first = prompt_fingerprint()
    monkeypatch.setattr(assistant, "TOOLS", assistant.TOOLS[:-1])
    assert prompt_fingerprint() != first


def test_the_report_says_which_model_prompt_date_and_settings_produced_the_numbers():
    records = run_questions([Q], lambda _: answer("fine"))
    report = build_report(records, repeat=3, date_used="2026-11-06", date_pinned=True)
    assert report["provider"] == "anthropic" and report["model"] == "test-model-from-env"
    assert report["prompt_hash"] == prompt_fingerprint()
    assert (report["date_used"], report["date_pinned"], report["repeat"]) == ("2026-11-06", True, 3)
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", report["timestamp_utc"])
    assert report["summary"]["runs"] == 1 and report["runs"] == records


def test_the_report_file_is_written_where_asked_and_never_holds_a_key(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret-value-for-test")
    records = run_questions([Q], lambda _: answer("a fine answer"))
    path = write_report(build_report(records, 1, "2026-11-06", True), tmp_path / "out" / "deeper")
    assert path.parent == tmp_path / "out" / "deeper" and re.fullmatch(r"eval-\d{8}T\d{6}Z-[0-9a-f]{8}\.json", path.name)
    text = path.read_text(encoding="utf-8")
    assert "sk-secret-value-for-test" not in text and "a fine answer" in text
    assert json.loads(text)["summary"]["passed"] == 1


def test_two_reports_in_the_same_second_never_overwrite_each_other(tmp_path):
    report = build_report(run_questions([Q], lambda _: answer()), 1, "2026-11-06", True)
    first, second = write_report(report, tmp_path), write_report(report, tmp_path)
    assert first != second and first.exists() and second.exists()
    assert len(list(tmp_path.glob("eval-*.json"))) == 2


# ---------------------------------------------------------------- main(): the command
def questions_file(tmp_path, *questions):
    path = tmp_path / "questions.json"
    path.write_text(json.dumps(list(questions)), encoding="utf-8")
    return path


def run_main(tmp_path, argv, ask_fn, questions, **kwargs):
    loaded = []
    code = main([*argv, "--out", str(tmp_path / "results")], ask_fn=ask_fn, env_loader=lambda: loaded.append(1),
                questions_path=questions_file(tmp_path, *questions), **kwargs)
    return code, loaded


def test_main_exits_0_when_everything_passes_prints_the_labels_and_writes_a_report(tmp_path, capsys):
    qs = [{**Q, "id": "q1", "must_include": ["ok"]}, {**Q, "id": "q2", "must_include": ["ok"]}]
    code, loaded = run_main(tmp_path, [], lambda q: answer("ok"), qs)
    out = capsys.readouterr().out
    assert code == 0 and loaded == [1]                           # the .env loader ran once, and only that
    assert "passed 2/2 runs (100%)" in out and "test-model-from-env" in out and prompt_fingerprint() in out
    [report] = list((tmp_path / "results").glob("eval-*.json"))
    assert json.loads(report.read_text())["repeat"] == 1         # one run per question by default
    assert str(report.name) in out


def test_main_exits_1_and_names_each_failing_run(tmp_path, capsys):
    qs = [{**Q, "id": "q1", "must_include": ["ok"]}, {**Q, "id": "q2", "must_include": ["never said"]}]
    code, _ = run_main(tmp_path, ["--repeat", "2"], lambda q: answer("ok"), qs)
    out = capsys.readouterr().out
    assert code == 1
    assert "passed 2/4 runs (50%)" in out and "q2 run 1: missing: never said" in out and "q2 run 2:" in out
    assert re.search(r"q1\s+2/2", out) and re.search(r"q2\s+0/2", out)


def test_only_selects_questions_and_an_unknown_id_is_a_setup_error(tmp_path, capsys):
    qs = [{**Q, "id": "q1"}, {**Q, "id": "q2"}]
    asked = []
    code, _ = run_main(tmp_path, ["--only", "q2"], lambda q: asked.append(q["id"]) or answer(), qs)
    assert code == 0 and asked == ["q2"]
    code, _ = run_main(tmp_path, ["--only", "q2,q99"], lambda q: asked.append("never") or answer(), qs)
    assert code == 2 and "q99" in capsys.readouterr().out and "never" not in asked


@pytest.mark.parametrize("bad", ["0", "-1", "two"])
def test_repeat_must_be_a_positive_whole_number(tmp_path, bad):
    with pytest.raises(SystemExit) as stopped:
        run_main(tmp_path, ["--repeat", bad], lambda q: answer(), [Q])
    assert stopped.value.code == 2


def test_a_missing_key_is_a_plain_message_and_exit_code_2_with_no_calls(tmp_path, monkeypatch, capsys):
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    code = main(["--out", str(tmp_path)], env_loader=lambda: [], questions_path=questions_file(tmp_path, Q))
    out = capsys.readouterr().out
    assert code == 2 and "not set up" in out.lower() and "traceback" not in out.lower()
    assert not list(tmp_path.glob("eval-*.json"))


def test_the_date_is_pinned_unless_you_set_one_or_ask_for_the_live_date(tmp_path, monkeypatch):
    seen = []
    def spy(q):
        seen.append(os.environ.get("CONCIERGE_TODAY"))
        return answer()
    monkeypatch.delenv("CONCIERGE_TODAY")
    run_main(tmp_path, [], spy, [Q])
    monkeypatch.setenv("CONCIERGE_TODAY", "2027-01-01")
    run_main(tmp_path, [], spy, [Q])
    run_main(tmp_path, ["--live-date"], spy, [Q])
    assert seen == ["2026-11-06", "2027-01-01", None]
    assert os.environ["CONCIERGE_TODAY"] == "2027-01-01"         # put back afterwards


def test_the_report_records_whether_the_date_was_pinned(tmp_path, monkeypatch):
    monkeypatch.delenv("CONCIERGE_TODAY")
    run_main(tmp_path, [], lambda q: answer(), [Q])
    run_main(tmp_path, ["--live-date"], lambda q: answer(), [Q])
    pinned, live = sorted((json.loads(p.read_text()) for p in (tmp_path / "results").glob("eval-*.json")),
                          key=lambda r: not r["date_pinned"])
    assert (pinned["date_used"], pinned["date_pinned"]) == ("2026-11-06", True)
    assert live["date_pinned"] is False and live["date_used"] == date.today().isoformat()
