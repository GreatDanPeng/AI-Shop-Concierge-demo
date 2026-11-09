[← Back to README](../README.md)

# Evals
`python -m evals.run_evals` asks 20 questions through the real assistant loop and prints a pass rate. It needs a key in `.env`. Useful options: `--repeat 3` (runs per question; the default is 1 so nothing spends money by surprise), `--only q1,q14`, `--live-date`. A JSON report with every answer, the tools called and each problem goes to `evals/results/` (git-ignored).

Every result is labelled with the provider and model, a short hash of the system rules and tools, the date used, and the repeat count. A run is repeatable by default: the "as of" date is pinned to 2026-11-06 (unless `CONCIERGE_TODAY` is set) and the catalog is the original six stores; the four brand questions switch the brand offers on for themselves.

The checks are keyword, tool-call and link heuristics (`evals/checks.py`): the words an answer must or must not contain, which tools it must or must not have called (prices must come from `best_combination`, best deals from `list_all_eligible_offers`), and that every link is one the server offered. They catch obvious mistakes, not subtle ones, and a failing check is not automatically the model's fault, so read the answer first (two of the findings below were real, and one early checker of mine was too strict).

| Date | Model | Prompt hash | Runs | Passed | Notes |
| --- | --- | --- | --- | --- | --- |
| 2026-11-08 | `deepseek/deepseek-v4.1-flash-1017` via OpenRouter | `8c04d741` | 20 questions x 3 | 58 of 60 (97%) | q14 (a non-English question): the model rewrote the link text in 2 of 3 answers |
| 2026-11-08 | same | `a9ad2358` | 20 questions x 3 | 60 of 60 (100%) | after two fixes (below); no answer names two different dates |
| 2026-11-08 | same | `a9ad2358` | q14 x 10 | 8 of 10 (80%) | one link text translated again, one link left out |

What the run found, both logged in [AI_MISTAKES.md](AI_MISTAKES.md): links lose their exact text when the member asks a non-English question (the rule now says what to translate; still not perfect), and the model sometimes quoted a date stamped in the data files instead of the live date (that stamp is no longer shown to the model). One model, one day, small samples: a smoke test, not a benchmark.
