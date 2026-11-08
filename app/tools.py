"""Tools the model may call. The member is bound by the server, never by the model.

Design rules:
- No tool takes a member id. dispatch() refuses any argument that tries to.
- Results contain only what the answer needs: no names, no emails, no documents.
- Offer "terms" text is untrusted data (it could contain instructions), so it is
  returned under the key "terms_untrusted" and the system prompt must say so.
  list_store_offers (the catalog) leaves the terms text out entirely.
"""
from __future__ import annotations

from datetime import date

from .catalog import load_offers, load_stores
from .engine import (DEMO_TODAY, best_combination, eligible_offers,
                     explain_ineligibility, load_members)
from .links import add_link, link_applied_offers
from .money import format_cents, with_dollars

FORBIDDEN_ARGS = {"member_id", "user_id", "member", "email", "name"}
MAX_CART_CENTS = 100_000_000  # $1,000,000.00: far above any demo cart; the web API uses the same limit

TOOLS = [
    {
        "name": "get_eligible_offers",
        "description": "List the offers the current member can use at one store, right now.",
        "input_schema": {
            "type": "object",
            "properties": {"store_id": {"type": "string", "description": "Store id, for example s1."}},
            "required": ["store_id"],
        },
    },
    {
        "name": "list_store_offers",
        "description": "List every offer at one store (public details only), including offers the "
                       "current member cannot use. Use it to find an offer_id, then call "
                       "explain_ineligibility to learn why the member can or cannot use it.",
        "input_schema": {
            "type": "object",
            "properties": {"store_id": {"type": "string", "description": "Store id, for example s1."}},
            "required": ["store_id"],
        },
    },
    {
        "name": "list_all_eligible_offers",
        "description": "List every offer the current member can use right now, across all stores, "
                       "largest percentage first (it is not a ranking by money saved: that needs a "
                       "cart total, so use best_combination for it). Takes no arguments. Use it when "
                       "the member asks about their best deals or discounts and no store is named.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "best_combination",
        "description": "For a cart total in cents at one store, return the combination of offers "
                       "with the largest savings and what the member pays.",
        "input_schema": {
            "type": "object",
            "properties": {
                "store_id": {"type": "string"},
                "cart_cents": {"type": "integer", "description": "Cart total in cents, for example 20000 for $200.00."},
            },
            "required": ["store_id", "cart_cents"],
        },
    },
    {
        "name": "explain_ineligibility",
        "description": "Explain why the current member cannot use a given offer (empty reasons = eligible).",
        "input_schema": {
            "type": "object",
            "properties": {"offer_id": {"type": "string"}},
            "required": ["offer_id"],
        },
    },
]


def _public_offer(o: dict) -> dict:
    return {
        "offer_id": o["id"],
        "store_id": o["store_id"],
        "type": o["type"],
        "headline_percent": o["headline_bps"] / 100,
        "groups": o.get("groups", []),
        "excluded_items": o.get("excluded_items", []),
        "annual_cap_cents": o.get("annual_cap_cents"),
        "annual_cap_dollars": (format_cents(o["annual_cap_cents"])
                               if o.get("annual_cap_cents") is not None else None),
        "stackable_with_cash_back": o.get("stackable_with_cash_back", True),
        "expires_on": o.get("expires_on"),
        "as_of": o.get("as_of"),
        "terms_untrusted": o.get("terms", ""),
    }


def _catalog_offer(o: dict) -> dict:
    """Public offer details for the catalog: the same fields, without the untrusted terms text."""
    public = _public_offer(o)
    del public["terms_untrusted"]
    return public


def _all_eligible_offers(member: dict, stores_by_id: dict, today: date, offers: list) -> list[dict]:
    """Every offer the member can use at any known store: public fields without the untrusted terms
    text, plus the store's name and link, the largest percentage first (ties by offer id)."""
    found = [o for store_id in stores_by_id for o in eligible_offers(member, store_id, today, offers)]
    found.sort(key=lambda o: (-o["headline_bps"], o["id"]))
    return [add_link({**_catalog_offer(o), "store_name": stores_by_id[o["store_id"]].get("name", "")},
                     o, stores_by_id) for o in found]


def dispatch(name: str, args, *, member_id: str, today: date = DEMO_TODAY,
             offers=None, members=None, stores=None) -> dict:
    """Run one tool call for the member the SERVER bound to this session."""
    if not isinstance(args, dict):
        return {"error": "bad_arguments"}
    if FORBIDDEN_ARGS & set(args):
        return {"error": "forbidden_argument"}

    members = load_members() if members is None else members
    offers = load_offers() if offers is None else offers
    stores_by_id = {s["id"]: s for s in (load_stores() if stores is None else stores)}
    member = next((m for m in members if m["id"] == member_id), None)
    if member is None:
        return {"error": "unknown_member"}

    if name == "get_eligible_offers":
        store_id = args.get("store_id")
        if not isinstance(store_id, str):
            return {"error": "bad_arguments"}
        found = eligible_offers(member, store_id, today, offers)
        return {"store_id": store_id, "as_of": today.isoformat(),
                "offers": [add_link(_public_offer(o), o, stores_by_id) for o in found]}

    if name == "list_all_eligible_offers":  # takes no arguments; any it is given are ignored
        return {"as_of": today.isoformat(),
                "offers": _all_eligible_offers(member, stores_by_id, today, offers)}

    if name == "list_store_offers":
        store_id = args.get("store_id")
        if not isinstance(store_id, str):
            return {"error": "bad_arguments"}
        return {"store_id": store_id, "as_of": today.isoformat(),
                "offers": [_catalog_offer(o) for o in offers if o["store_id"] == store_id]}

    if name == "best_combination":
        store_id, cart = args.get("store_id"), args.get("cart_cents")
        if not isinstance(store_id, str) or type(cart) is not int or not 0 < cart <= MAX_CART_CENTS:
            return {"error": "bad_arguments"}
        result = with_dollars(best_combination(member, store_id, cart, today, offers))
        return link_applied_offers(result, offers, stores_by_id)

    if name == "explain_ineligibility":
        offer_id = args.get("offer_id")
        offer = next((o for o in offers if o["id"] == offer_id), None) if isinstance(offer_id, str) else None
        if offer is None:
            return {"error": "unknown_offer"}
        reasons = explain_ineligibility(member, offer, today)
        return {"offer_id": offer["id"], "eligible": not reasons, "reasons": reasons,
                "as_of": today.isoformat()}

    return {"error": "unknown_tool"}
