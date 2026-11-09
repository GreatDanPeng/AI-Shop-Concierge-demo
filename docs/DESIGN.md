[← Back to README](../README.md)

# Design

## How it works
```
 browser:  shop page (React)  +  widget.js (React in a shadow root)
              |  GET /me /discounts /estimate        |  POST /chat
              v                                      v
 FastAPI (same origin, cookie says WHO)  ---->  assistant loop ---> model (tool use)
              |                                      |
        matching service                        tools (read-only)
              +--------------> rules engine <---------+
```
- **Identity matching** (`app/matching.py`) is plain code: it asks the rules engine, per offer, whether the member qualifies and why not. No model is involved.
- **The assistant** (`app/assistant.py`) can only use the read-only tools in `app/tools.py`, always for the member the server bound to the session.

## Design decisions
1. **The model talks; code decides.** Eligibility and prices are computed by deterministic code and reached through tools, so the assistant cannot invent a discount.
2. **Member binding on the server.** Tools take no member id; the session decides who is asking, so the model cannot read another member's data. The member never travels in a request body or query.
3. **Minimal data to the model.** Tool results carry offers and reason codes, not names, emails or documents.
4. **Untrusted text.** Offer terms are returned as `terms_untrusted`. One fixture offer (`o99`) contains an injection attempt on purpose, and a test and an eval check that it changes nothing. The page renders model text as plain text, with only bold and lists as elements.
5. **Honest about change.** Every answer carries an "as of" date (today's real date, from `app/clock.py`) and makes no guarantee, because offers can change at any time. The concierge window itself shows no fixed disclaimer; the wording comes with each answer.
6. **Helpful over profitable.** Ranking uses the member's total savings only, not what a store pays.
7. **Nobody converts cents.** A live run showed the model turning 130000 cents into "$130.00". The server now produces every dollar string once (`app/money.py`, integer math); the model and the page only copy them. See the first row of [AI_MISTAKES.md](AI_MISTAKES.md).
8. **Only what you qualify for.** The page never shows an offer you do not qualify for, and hides a store with none; the concierge explains why an offer is missing.
9. **Tokens, not literals.** Every colour, radius, spacing step, shadow, font size and motion duration lives in `web/src/design/tokens.css` (light, dark, reduced motion). A test fails if one appears anywhere else, and others check AA contrast in both themes.
10. **The server writes the links.** When the concierge names an offer you can use, it copies a ready-made link (`link_markdown`, from `app/links.py`) such as `[Cobalt Shoes: 4% cash back](#/store/s4)`, which opens that store page in this shop. The model never builds an address, offers you cannot use get no link, and the page turns a link into a link only when its address is exactly `#/store/<id>`; anything else (`https://...`, `javascript:`, `..`) stays visible text. This stops an offer's untrusted terms text from steering the model into a bad link.
11. **Invented offers under familiar names, kept honest.** The brand offers live in their own files (`data/brand_stores.json`, `data/brand_offers.json`) and `app/catalog.py` serves them instead of the original six stores (or the original six, when the switch is off); the rules engine is untouched and every test outside the brand files runs on the original six. Each brand store's description says the offers are invented, the footer says no brand offers these discounts, and the concierge's rules tell it to say so if asked. Logos are the owners' trademarks, kept in `web/public/brands/` with their sources and licence tags in `SOURCES.md`; a disclaimer is not permission, so check each brand's own guidelines before using them anywhere else, and `logo: null` brings a store's illustration back (`web/public/brands/SOURCES.md` explains how).

## Look and feel
The look follows [UI_DESIGN.md](UI_DESIGN.md): a calm, Copilot-style design (pastel gradient, intent-first input, collapsible sidebar), with no Microsoft branding. The page is organised like a deals marketplace (categories, featured offers, store tiles, store pages), without any real marketplace's logo, copy or styling (the brand logos shown on store tiles are listed in `web/public/brands/SOURCES.md`). Dark mode follows the system setting; there is no light/dark switch on the page (the widget still accepts `setTheme` for pages that embed it). Each brand store shows its brand's logo, with an original illustration as the fallback (the six original stores use illustrations); you can swap in photos you are licensed to use, see [IMAGES.md](IMAGES.md).

## Assumptions (also returned by `best_combination`)
- Cash back is calculated on the amount paid after any group discount.
- Group discounts do not combine; the best one is chosen.
- A verification is valid for 365 days.
