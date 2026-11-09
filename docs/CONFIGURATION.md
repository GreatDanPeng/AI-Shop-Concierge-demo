[← Back to README](../README.md)

# Configuration

## Running without Docker
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then put your key in .env (git-ignored)
(cd web && npm install && npm run build)
uvicorn app.server:app --reload
# open http://127.0.0.1:8000
```
Without a key the page and the discount matching still work; only the concierge reports that it is not set up.

Tests: `pytest -q` and `cd web && npm test` (plus `npm run typecheck`).
Working on the page: `cd web && npm run build:widget && npm run dev` (Vite proxies the API to port 8000).

## Environment variables (`.env`)
| Variable | Meaning |
| --- | --- |
| `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | Use OpenRouter (cheap models for testing). The model id is not in the code. |
| `ANTHROPIC_API_KEY` (or `ANTHROPIC_AUTH_TOKEN`), `ANTHROPIC_MODEL` | Use Anthropic instead |
| `LLM_PROVIDER` | `openrouter` or `anthropic`. If unset: OpenRouter when its key is set, else Anthropic |
| `CONCIERGE_BRAND_OFFERS` | Optional. Unset or anything else: the app serves the 12 brand stores (invented offers, real brand logos). `off`, `0`, `false` or `no`: it serves the six original invented stores instead. One or the other, never both. Read on every request |
| `CONCIERGE_TODAY` | Optional, `YYYY-MM-DD`. Pins the "as of" date (for repeatable demos, evals and tests). Unset means today's real date, in the server's time zone. A bad value is ignored with a warning |

A key for one provider is never sent to the other. Never set `ANTHROPIC_LOG=debug` expecting to see requests: the code keeps the SDK's debug logs off because they contain the member's message.

## Brand offers: familiar names, invented offers
To make a demo recognisable, the app shows 12 well-known brands (Apple, lululemon, Nike, Samsung, IKEA and others) with offers I made up, for example teachers get 20% off a new Apple computer and military members get 15% off at lululemon. None of these brands offers these discounts and none is involved: the page footer, every one of these stores' descriptions and the concierge all say so. Each store shows its brand's own logo (an original illustration is the fallback if a logo cannot load); the logos are their owners' trademarks, so see the Disclaimer in the [README](../README.md) and `web/public/brands/SOURCES.md` for where each came from. There are no brand photos. Only brands with a free logo file are included (REI was dropped for that reason). Set `CONCIERGE_BRAND_OFFERS=off` to swap them for the six original invented stores (Fjordline, Voltage, Inkwell, Cobalt, Harbor & Hearth, Lumen), which the tests and the eval questions use.

## Using the widget on another page
```html
<script src="/widget.js" data-store-id="s7" data-store-name="Apple" defer></script>
```
The page can then call `window.Concierge.setStore(id, name)`, `.open()`, `.close()`, `.ask(text)` (opens the panel and sends a question) and `.setTheme('auto' | 'light' | 'dark')`. The widget lives in a shadow root, so page styles cannot break it. Another origin needs `data-api-base` and CORS on the server (not set up). Links in answers are written as `#/store/<id>`, which resolves against the page that hosts the widget, so they only work on this shop (a `data-link-base` option would fix that for other sites; not built).
