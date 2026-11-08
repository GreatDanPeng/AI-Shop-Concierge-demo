"""Run the eval questions against the assistant and print a pass rate.

    python -m evals.run_evals [--repeat N] [--only q1,q2] [--live-date] [--out DIR]

Every result is labelled with the provider and model, a short hash of the system prompt and tools, the date
used and the repeat count, because a pass rate without those means nothing a week later. By default the run
is repeatable: the "as of" date is pinned to 2026-11-06 (unless CONCIERGE_TODAY is set; --live-date uses the
real date) and the catalog is the original six invented stores (a question can ask for "catalog": "brands").
One run per question unless --repeat says more, so nothing spends money by surprise.

The checks are keyword and tool-call heuristics (evals/checks.py). Read a failing answer before blaming the
model: a check that is too strict looks the same as a model that is wrong. A JSON report with every answer
goes to evals/results/ (git-ignored). Exit codes: 0 all passed, 1 some failed, 2 a setup problem.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app import assistant
from app.assistant import AssistantUnavailable, ConfigError, build_client, provider_status, run_assistant
from app.catalog import BRANDS_VARIABLE, load_stores
from app.clock import PIN_VARIABLE, today
from app.env import load_env_file
from app.tools import dispatch

from .checks import check_answer

QUESTIONS = Path(__file__).resolve().parent / "questions.json"
RESULTS = Path(__file__).resolve().parent / "results"
PINNED_DATE = "2026-11-06"


@dataclass(frozen=True)
class Answer:
    """What one question produced: the reply, the tools called, how the loop ended, the links on offer."""
    text: str
    tool_names: list[str] = field(default_factory=list)
    status: str = "ok"
    allowed_links: frozenset = frozenset()


@contextlib.contextmanager
def _environment(name: str, value: str | None):
    """Set (or, with None, unset) an environment variable for a while, then put it back as it was."""
    previous = os.environ.get(name)
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


def _offered_links(member_id: str) -> frozenset:
    """Every link the server would hand the model for this member, at any store."""
    links = set()
    for store in load_stores():
        found = dispatch("get_eligible_offers", {"store_id": store["id"]}, member_id=member_id, today=today())
        links.update(o["link_markdown"] for o in found.get("offers", []) if "link_markdown" in o)
    return frozenset(links)


def ask(question: dict, client=None) -> Answer:
    """Put one question through the real assistant loop, as the question's member, at its store (or none)."""
    brands = "on" if question.get("catalog") == "brands" else "off"
    with _environment(BRANDS_VARIABLE, brands):
        result = run_assistant(question["question"], question["member_id"], question.get("store_id"),
                               client=client)
        links = _offered_links(question["member_id"])
    return Answer(result.reply, [call["name"] for call in result.tool_calls], result.status, links)


def _one_run(question: dict, run: int, ask_fn) -> dict:
    base = {"id": question["id"], "run": run, "catalog": question.get("catalog", "original")}
    try:
        got = ask_fn(question)
    except AssistantUnavailable:
        return {**base, "passed": False, "problems": ["assistant unavailable"], "answer": "", "tools": [],
                "error": True}
    if got.status != "ok":  # the reply is the apology, so word checks on it would only mislead
        problems = [f"assistant gave up: {got.status}"]
    else:
        problems = check_answer(got.text, question, got.tool_names, got.allowed_links)
    return {**base, "passed": not problems, "problems": problems, "answer": got.text, "tools": got.tool_names,
            "error": False}


def run_questions(questions: list[dict], ask_fn, repeat: int = 1) -> list[dict]:
    """Ask every question `repeat` times, in order. A setup problem (ConfigError) is not swallowed."""
    if repeat < 1:
        raise ValueError("repeat must be at least 1")
    return [_one_run(q, run, ask_fn) for q in questions for run in range(1, repeat + 1)]


def summarise(records: list[dict]) -> dict:
    per_question: dict[str, dict] = {}
    for r in records:
        counts = per_question.setdefault(r["id"], {"passed": 0, "runs": 0})
        counts["runs"] += 1
        counts["passed"] += r["passed"]
    passed = sum(r["passed"] for r in records)
    runs = len(records)
    return {
        "per_question": per_question, "passed": passed, "runs": runs,
        "errors": sum(r["error"] for r in records),
        "percent": (passed * 100 + runs // 2) // runs if runs else None,  # half-up, integers only
        "failures": [r for r in records if not r["passed"]],
    }


def prompt_fingerprint() -> str:
    """A short hash of the system rules and the tool definitions: it changes when either does."""
    material = assistant.SYSTEM_RULES + json.dumps(assistant.TOOLS, sort_keys=True)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:8]


def build_report(records: list[dict], repeat: int, date_used: str, date_pinned: bool) -> dict:
    status = provider_status()  # provider and model id only, never a key
    return {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "provider": status["provider"], "model": status["model"], "prompt_hash": prompt_fingerprint(),
        "date_used": date_used, "date_pinned": date_pinned, "repeat": repeat,
        "default_catalog": "original", "summary": summarise(records), "runs": records,
    }


def write_report(report: dict, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = report["timestamp_utc"].replace("-", "").replace(":", "")
    path = out_dir / f"eval-{stamp}-{report['prompt_hash']}.json"
    number = 1
    while path.exists():  # two runs in the same second must never overwrite each other's results
        number += 1
        path = out_dir / f"eval-{stamp}-{report['prompt_hash']}-{number}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a whole number of at least 1") from None
    if value < 1:
        raise argparse.ArgumentTypeError("must be a whole number of at least 1")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m evals.run_evals", description=__doc__.split("\n\n")[0])
    parser.add_argument("--repeat", type=_positive_int, default=1, help="runs per question (default 1)")
    parser.add_argument("--only", help="comma-separated question ids to run, for example q1,q9")
    parser.add_argument("--live-date", action="store_true", help="use the real date instead of the pinned one")
    parser.add_argument("--out", type=Path, default=RESULTS, help="where the JSON report goes")
    return parser


def _print_results(records, summary, label, out_path) -> None:
    questions = {r["id"]: r for r in records}
    print(label)
    for qid, counts in summary["per_question"].items():
        print(f"{qid:<6}{counts['passed']}/{counts['runs']}  {questions[qid].get('question', '')}")
    print(f"\npassed {summary['passed']}/{summary['runs']} runs ({summary['percent']}%), {summary['errors']} errors")
    if summary["failures"]:
        print("failures:")
        for f in summary["failures"]:
            print(f"  {f['id']} run {f['run']}: {'; '.join(f['problems'])}")
    print(f"report: {out_path}")


def main(argv=None, *, ask_fn=None, env_loader=load_env_file, questions_path: Path = QUESTIONS) -> int:
    args = _parser().parse_args(argv)
    env_loader()
    questions = json.loads(Path(questions_path).read_text(encoding="utf-8"))
    if args.only:
        wanted = [i.strip() for i in args.only.split(",") if i.strip()]
        unknown = [i for i in wanted if i not in {q["id"] for q in questions}]
        if unknown:
            print(f"unknown question id(s): {', '.join(unknown)}")
            return 2
        questions = [q for q in questions if q["id"] in wanted]
    try:
        if ask_fn is None:
            if not provider_status()["configured"]:
                print("The assistant is not set up (no key or model id; see the README), so there is nothing to "
                      "evaluate.")
                return 2
            client = build_client()
            ask_fn = lambda q: ask(q, client)  # noqa: E731
        pin = None if args.live_date else (os.environ.get(PIN_VARIABLE, "").strip() or PINNED_DATE)
        with _environment(PIN_VARIABLE, pin):
            date_used = today().isoformat()
            records = run_questions(questions, ask_fn, args.repeat)
    except ConfigError as exc:
        print(f"setup problem: {exc}")
        return 2
    # the report and the printed table carry the question text, which the records do not
    for r in records:
        r.setdefault("question", next(q["question"] for q in questions if q["id"] == r["id"]))
    report = build_report(records, args.repeat, date_used, date_pinned=not args.live_date)
    path = write_report(report, args.out)
    label = (f"{report['provider']} / {report['model']} | prompt {report['prompt_hash']} | date {date_used} "
             f"({'live' if args.live_date else 'pinned'}) | repeat {args.repeat} | {len(questions)} questions")
    _print_results(records, report["summary"], label, path)
    return 0 if not report["summary"]["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
