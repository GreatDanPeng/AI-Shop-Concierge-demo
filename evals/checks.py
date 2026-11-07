"""Simple, explainable checks for an assistant answer (case-insensitive substring).

These are heuristics, not a proof of quality. Say so in the README, and add
checks that look at the tool calls the assistant made (for example, that it
called best_combination before quoting a price).
"""


def check_answer(answer: str, question: dict) -> list[str]:
    """Return a list of problems; an empty list means the answer passed."""
    low = answer.lower()
    problems = []
    for text in question.get("must_include", []):
        if text.lower() not in low:
            problems.append(f"missing: {text}")
    for text in question.get("must_not_include", []):
        if text.lower() in low:
            problems.append(f"forbidden: {text}")
    return problems
