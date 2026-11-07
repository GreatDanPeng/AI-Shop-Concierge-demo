# Concierge demo (unofficial concept demo, fake data)

> Not affiliated with ID.me. All stores, offers and members are invented. The matching rules are my assumptions from public pages, not ID.me's implementation.

## What this is
A small AI shopping concierge: a chat assistant that tells a signed-in member which offers they qualify for, what the best combination saves, and why an offer is not showing, without making up discounts and without exposing member data.

## Status
| Part | State |
| --- | --- |
| Fake data (stores, offers, members) | Done |
| Rules engine and tests | Done (starter) |
| Tool layer with server-side member binding | Done (starter) |
| FastAPI skeleton | Done, assistant loop is a TODO |
| Claude loop (`run_assistant`) | TODO |
| Demo Shop page and `widget.js` | TODO |
| Eval run and pass rate | TODO |
| AI mistakes log | TODO (real entries only) |

## Run
```bash
pip install -r requirements.txt
pytest -q
```

## Design decisions
1. **The model talks; code decides.** Eligibility and prices are computed by deterministic code and reached through tools, so the assistant cannot invent a discount.
2. **Member binding on the server.** Tools take no member id; the session decides who is asking, so the model cannot read another member's data.
3. **Minimal data to the model.** Tool results carry offers and reason codes, not names, emails or documents.
4. **Untrusted text.** Offer terms are returned as `terms_untrusted`. One fixture offer (`o99`) contains an injection attempt on purpose, and a test and an eval check that it changes nothing.
5. **Honest about change.** Every answer carries an "as of" date and makes no guarantee, because offers can change at any time.
6. **Helpful over profitable.** Ranking uses the member's total savings only, not what a store pays.

## Assumptions (also returned by `best_combination`)
- Cash back is calculated on the amount paid after any group discount.
- Group discounts do not combine; the best one is chosen.
- A verification is valid for 365 days.

## Evals
`evals/questions.json` holds the question set; `python -m evals.run_evals` runs it. Results: _TODO (pass rate, which questions fail and why)_. The checks are keyword heuristics, so they catch obvious errors, not subtle ones.

## AI mistakes log
See [docs/AI_MISTAKES.md](docs/AI_MISTAKES.md).

## Not built (on purpose)
Real login, a database, deployment, streaming, real store data.
