"""Rules engine for the concierge demo (unofficial concept demo, fake data).

Everything that must be correct (who is eligible, what a discount is worth)
lives here, in plain code. The language model never computes these.
Money is integer cents. Percentages are basis points (1% = 100 bps).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
VERIFICATION_DAYS = 365
DEMO_TODAY = date(2026, 11, 6)  # fixed so the demo and tests are deterministic

ASSUMPTIONS = [
    "Matching rules are assumptions based on public pages, not ID.me's implementation.",
    "Cash back is calculated on the amount paid after any group discount.",
    "Group discounts do not combine with each other; the best one is chosen.",
    "Offers can change at any time; figures are as of the date shown.",
]


def _load(name: str):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def load_stores():
    return _load("stores.json")


def load_offers():
    return _load("offers.json")


def load_members():
    return _load("members.json")


def pct_half_up(amount_cents: int, bps: int) -> int:
    """Percentage of an amount in whole cents, rounded half-up, integer math only.

    Do not use round(): Python rounds half to even (round(0.5) == 0).
    """
    return (amount_cents * bps + 5000) // 10000


def verification_status(member: dict, group: str, today: date) -> str:
    """Return "valid", "expired" or "missing" for one group."""
    verified_on = member.get("verifications", {}).get(group)
    if verified_on is None:
        return "missing"
    age_days = (today - date.fromisoformat(verified_on)).days
    if age_days < 0:  # a verification dated in the future is not valid
        return "missing"
    return "valid" if age_days < VERIFICATION_DAYS else "expired"


def explain_ineligibility(member: dict, offer: dict, today: date = DEMO_TODAY) -> list[str]:
    """Sorted reason codes why the member cannot use the offer; [] means eligible.

    Codes: OFFER_EXPIRED, NOT_VERIFIED, VERIFICATION_EXPIRED, CAP_REACHED.
    """
    reasons = []
    expires = offer.get("expires_on")
    if expires and today > date.fromisoformat(expires):
        reasons.append("OFFER_EXPIRED")

    groups = offer.get("groups", [])
    if groups:  # an empty list means every member qualifies (cash back)
        statuses = [verification_status(member, g, today) for g in groups]
        if "valid" not in statuses:
            reasons.append("VERIFICATION_EXPIRED" if "expired" in statuses else "NOT_VERIFIED")

    cap = offer.get("annual_cap_cents")
    spent = member.get("annual_spend_cents", {}).get(offer["id"], 0)
    if cap is not None and spent >= cap:
        reasons.append("CAP_REACHED")
    return sorted(reasons)


def eligible_offers(member: dict, store_id: str, today: date = DEMO_TODAY, offers=None) -> list[dict]:
    if offers is None:
        offers = load_offers()
    return [o for o in offers
            if o["store_id"] == store_id and not explain_ineligibility(member, o, today)]


def _group_discount_cents(member: dict, offer: dict, cart_cents: int) -> int:
    """Discount in cents, limited to the part of the cart still under the annual cap."""
    cap = offer.get("annual_cap_cents")
    if cap is None:
        base = cart_cents
    else:
        remaining = cap - member.get("annual_spend_cents", {}).get(offer["id"], 0)
        base = min(cart_cents, max(remaining, 0))
    return pct_half_up(base, offer["headline_bps"])


def best_combination(member: dict, store_id: str, cart_cents: int,
                     today: date = DEMO_TODAY, offers=None) -> dict:
    """Pick the combination with the largest total savings for this cart.

    Raises ValueError if cart_cents is not a positive int (bool is rejected).
    """
    if type(cart_cents) is not int or cart_cents <= 0:
        raise ValueError("cart_cents must be a positive integer")

    eligible = eligible_offers(member, store_id, today, offers)
    group_offers = [o for o in eligible if o["type"] == "group_discount"]
    cash_backs = [o for o in eligible if o["type"] == "cash_back"]
    best_cb = max(cash_backs, key=lambda o: (o["headline_bps"], o["id"]), default=None)

    options = []
    for g in [None] + group_offers:
        for c in [None] + ([best_cb] if best_cb else []):
            if g and c and not g.get("stackable_with_cash_back", True):
                continue
            discount = _group_discount_cents(member, g, cart_cents) if g else 0
            pay = cart_cents - discount
            cash_back = pct_half_up(pay, c["headline_bps"]) if c else 0
            options.append({
                "group": g, "cash_back_offer": c, "discount": discount,
                "pay": pay, "cash_back": cash_back, "total": discount + cash_back,
            })
    # highest total savings; ties broken by bigger upfront discount, then offer ids
    options.sort(key=lambda x: (-x["total"], -x["discount"],
                                x["group"]["id"] if x["group"] else "",
                                x["cash_back_offer"]["id"] if x["cash_back_offer"] else ""))
    best = options[0]
    g, c = best["group"], best["cash_back_offer"]
    return {
        "store_id": store_id,
        "cart_cents": cart_cents,
        "group_discount": ({"offer_id": g["id"], "cents": best["discount"],
                            "excluded_items": g.get("excluded_items", [])} if g and best["discount"] else None),
        "cash_back": ({"offer_id": c["id"], "cents": best["cash_back"]} if c and best["cash_back"] else None),
        "you_pay_cents": best["pay"],
        "cash_back_cents": best["cash_back"],
        "total_savings_cents": best["total"],
        "as_of": today.isoformat(),
        "assumptions": ASSUMPTIONS,
    }
