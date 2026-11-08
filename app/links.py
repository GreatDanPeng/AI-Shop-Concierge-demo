"""Links the server writes for the model to copy, so the model never builds an address.

A link always points inside this shop, to "#/store/<store id>", and its label is plain text with no
bracket, parenthesis or control character. That keeps the markdown one fixed shape: a store name or
an offer's untrusted `terms` text cannot change where a link goes, and a store id that is not a
plain token gets no link at all. The page applies the same address rule when it renders replies.
"""
from __future__ import annotations

import re

from .money import headline_label

_STORE_ID = re.compile(r"[A-Za-z0-9_-]+")
_NOT_ALLOWED_IN_LABEL = re.compile(r"[\[\]()\x00-\x1f\x7f]")


def _plain(name: object) -> str:
    """The name with brackets, parentheses and control characters replaced by spaces, then tidied."""
    return " ".join(_NOT_ALLOWED_IN_LABEL.sub(" ", str(name)).split())


def offer_label(store_name: object, offer: dict) -> str:
    """For example "Cobalt Shoes: 4% cash back" or "Fjordline Outdoors: 30% off"."""
    kind = "cash back" if offer.get("type") == "cash_back" else "off"
    return f"{_plain(store_name)}: {headline_label(offer['headline_bps'])} {kind}"


def offer_link(store: dict, offer: dict) -> dict | None:
    """{"label", "href", "markdown"} for an offer at this store, or None if the store id is unsafe."""
    store_id = store.get("id")
    if not isinstance(store_id, str) or not _STORE_ID.fullmatch(store_id):
        return None
    name = _plain(store.get("name", "")) or store_id  # a name with nothing left shows the id
    label = offer_label(name, offer)
    href = f"#/store/{store_id}"
    return {"label": label, "href": href, "markdown": f"[{label}]({href})"}


def add_link(public: dict, offer: dict, stores_by_id: dict) -> dict:
    """Put `link_markdown` on a public offer dict, if its store is known and its id is safe."""
    store = stores_by_id.get(offer.get("store_id"))
    link = offer_link(store, offer) if store else None
    if link:
        public["link_markdown"] = link["markdown"]
    return public


def link_applied_offers(result: dict, offers: list, stores_by_id: dict) -> dict:
    """Add `link_markdown` to the group discount and the cash back that best_combination applied."""
    offers_by_id = {o["id"]: o for o in offers}
    for key in ("group_discount", "cash_back"):
        applied = result.get(key)
        offer = offers_by_id.get(applied["offer_id"]) if applied else None
        if offer is not None:
            add_link(applied, offer, stores_by_id)
    return result
