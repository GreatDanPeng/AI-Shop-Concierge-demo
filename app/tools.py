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

from .engine import (DEMO_TODAY, best_combination, eligible_offers,
                     explain_ineligibility, load_members, load_offers)

FORBIDDEN_ARGS = {"member_id", "user_id", "member", "email", "name"}

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


def dispatch(name: str, args, *, member_id: str, today: date = DEMO_TODAY,
             offers=None, members=None) -> dict:
    """Run one tool call for the member the SERVER bound to this session."""
    if not isinstance(args, dict):
        return {"error": "bad_arguments"}
    if FORBIDDEN_ARGS & set(args):
        return {"error": "forbidden_argument"}

    members = load_members() if members is None else members
    offers = load_offers() if offers is None else offers
    member = next((m for m in members if m["id"] == member_id), None)
    if member is None:
        return {"error": "unknown_member"}

    if name == "get_eligible_offers":
        store_id = args.get("store_id")
        if not isinstance(store_id, str):
            return {"error": "bad_arguments"}
        found = eligible_offers(member, store_id, today, offers)
        return {"store_id": store_id, "as_of": today.isoformat(),
                "offers": [_public_offer(o) for o in found]}

    if name == "list_store_offers":
        store_id = args.get("store_id")
        if not isinstance(store_id, str):
            return {"error": "bad_arguments"}
        return {"store_id": store_id, "as_of": today.isoformat(),
                "offers": [_catalog_offer(o) for o in offers if o["store_id"] == store_id]}

    if name == "best_combination":
        store_id, cart = args.get("store_id"), args.get("cart_cents")
        if not isinstance(store_id, str) or type(cart) is not int or cart <= 0:
            return {"error": "bad_arguments"}
        return best_combination(member, store_id, cart, today, offers)

    if name == "explain_ineligibility":
        offer_id = args.get("offer_id")
        offer = next((o for o in offers if o["id"] == offer_id), None) if isinstance(offer_id, str) else None
        if offer is None:
            return {"error": "unknown_offer"}
        reasons = explain_ineligibility(member, offer, today)
        return {"offer_id": offer["id"], "eligible": not reasons, "reasons": reasons,
                "as_of": today.isoformat()}

    return {"error": "unknown_tool"}
