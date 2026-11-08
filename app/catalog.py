"""The catalog the app serves: the engine's stores and offers, plus invented offers from familiar brands.

The brand offers (data/brand_stores.json, data/brand_offers.json) make a demo recognisable to a general
audience. They are INVENTED: these brands do not offer these discounts and are not involved. They are on
by default and CONCIERGE_BRAND_OFFERS=off (also 0, false, no) switches them off, leaving only the original
invented stores. The switch is read on every call, so it needs no restart.

The rules engine is untouched. Its own loaders still return only the original data, which is what its
tests rely on; the tools, matching, server and assistant import their loaders from here.
"""
from __future__ import annotations

import json
import os
from typing import Mapping

from . import engine

BRANDS_VARIABLE = "CONCIERGE_BRAND_OFFERS"
_OFF_VALUES = {"off", "0", "false", "no"}


def brand_offers_on(environ: Mapping[str, str] | None = None) -> bool:
    """True unless the switch says off."""
    environ = os.environ if environ is None else environ
    return environ.get(BRANDS_VARIABLE, "").strip().lower() not in _OFF_VALUES


def _brand_data(name: str) -> list:
    with open(engine.DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def load_stores(environ: Mapping[str, str] | None = None) -> list:
    """The original stores first, then the brand stores (unless switched off)."""
    stores = engine.load_stores()
    return stores + _brand_data("brand_stores.json") if brand_offers_on(environ) else stores


def load_offers(environ: Mapping[str, str] | None = None) -> list:
    """The original offers first, then the brand offers (unless switched off)."""
    offers = engine.load_offers()
    return offers + _brand_data("brand_offers.json") if brand_offers_on(environ) else offers
