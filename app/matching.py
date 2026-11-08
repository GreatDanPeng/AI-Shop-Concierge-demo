"""Identity matching: which discounts a member matches, and why not.

Deterministic code only; no model involved. It reuses the rules engine (engine.py is unchanged)
and shapes the answers for the shop page. Nothing here carries the untrusted offer terms text
or any personal data beyond the member's own display name.
"""
from __future__ import annotations

from datetime import date, timedelta

from .catalog import load_offers, load_stores
from .engine import (DEMO_TODAY, VERIFICATION_DAYS, best_combination, explain_ineligibility,
                     verification_status)
from .links import link_applied_offers
from .money import format_cents, headline_label, with_dollars

# Fixed sentences for the engine's reason codes. {groups} is filled with the groups the offer is for.
REASON_TEXT = {
    "OFFER_EXPIRED": "This offer has ended.",
    "NOT_VERIFIED": "You haven't verified a group this offer is for ({groups}).",
    "VERIFICATION_EXPIRED": "Your verification has expired. Renew it to qualify.",
    "CAP_REACHED": "You've reached this offer's annual cap.",
}
UNKNOWN_REASON_TEXT = "This offer is not available to you right now."


def _group_label(group: str) -> str:
    return group.replace("_", " ")


def _reason_text(code: str, offer: dict) -> str:
    template = REASON_TEXT.get(code, UNKNOWN_REASON_TEXT)
    groups = ", ".join(_group_label(g) for g in offer.get("groups", []))
    return template.format(groups=groups)


def describe_identity(member: dict, today: date = DEMO_TODAY) -> dict:
    """The member's own identity: each verified group with its status and expiry date.

    No email. A verification dated in the future is reported as "missing" (as the engine does).
    """
    verifications = []
    for group, verified_on in sorted(member.get("verifications", {}).items()):
        expires_on = date.fromisoformat(verified_on) + timedelta(days=VERIFICATION_DAYS)
        verifications.append({
            "group": group,
            "status": verification_status(member, group, today),
            "verified_on": verified_on,
            "expires_on": expires_on.isoformat(),
        })
    return {"member_id": member["id"], "display_name": member["display_name"],
            "verifications": verifications}


def _match_one(member: dict, offer: dict, today: date) -> dict:
    reasons = explain_ineligibility(member, offer, today)
    return {
        "offer_id": offer["id"],
        "type": offer["type"],
        "headline_bps": offer["headline_bps"],
        "headline_label": headline_label(offer["headline_bps"]),
        "groups": offer.get("groups", []),
        "excluded_items": offer.get("excluded_items", []),
        "annual_cap_cents": offer.get("annual_cap_cents"),
        "annual_cap_dollars": (format_cents(offer["annual_cap_cents"])
                               if offer.get("annual_cap_cents") is not None else None),
        "stackable_with_cash_back": offer.get("stackable_with_cash_back", True),
        "expires_on": offer.get("expires_on"),
        "eligible": not reasons,
        "reasons": reasons,
        "reason_text": [_reason_text(code, offer) for code in reasons],
    }


def match_offers(member: dict, today: date = DEMO_TODAY, *, stores=None, offers=None) -> list[dict]:
    """Every store with every offer marked eligible or not, and the reasons why not."""
    stores = load_stores() if stores is None else stores
    offers = load_offers() if offers is None else offers
    return [
        {"store_id": s["id"], "name": s["name"], "blurb": s.get("blurb", ""),
         "category": s.get("category", "Other"), "art": s.get("art"),
         "image": s.get("image"), "image_credit": s.get("image_credit"),
         "offers": [_match_one(member, o, today) for o in offers if o["store_id"] == s["id"]]}
        for s in stores
    ]


def estimate(member: dict, store_id: str, cart_cents: int, today: date = DEMO_TODAY, *,
             offers=None, stores=None) -> dict:
    """The engine's best combination for a cart: cents, ready-made dollar strings, and a link to
    the store for each offer applied. The model's best_combination tool returns exactly the same.

    Raises ValueError for a bad cart.
    """
    offers = load_offers() if offers is None else offers
    stores = load_stores() if stores is None else stores
    result = with_dollars(best_combination(member, store_id, cart_cents, today, offers))
    return link_applied_offers(result, offers, {s["id"]: s for s in stores})
