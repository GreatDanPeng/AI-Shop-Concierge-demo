"""Run the eval questions against the assistant. Usage: python -m evals.run_evals

TODO: implement ask() by calling app.server.run_assistant (or the /chat endpoint).
Print the pass rate and the failing question ids, and paste the numbers in the README.
"""
import json
from pathlib import Path

from .checks import check_answer

QUESTIONS = Path(__file__).resolve().parent / "questions.json"


def ask(question: dict) -> str:
    raise NotImplementedError("wire this to the assistant")


def main() -> None:
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    failed = []
    for q in questions:
        problems = check_answer(ask(q), q)
        if problems:
            failed.append((q["id"], problems))
    passed = len(questions) - len(failed)
    print(f"{passed}/{len(questions)} passed")
    for qid, problems in failed:
        print(qid, problems)


if __name__ == "__main__":
    main()
