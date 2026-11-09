"""The catalog the app serves: invented offers from familiar brands, or the original invented stores.

With the brand offers ON (the default) the app serves ONLY the 12 brands that have a logo, with offers I
made up (data/brand_stores.json, data/brand_offers.json). They make a demo recognisable to a general
audience; they are INVENTED: these brands do not offer these discounts and are not involved. With
CONCIERGE_BRAND_OFFERS=off (also 0, false, no) the app serves only the six original invented stores
(data/stores.json, data/offers.json), which the starter tests and the eval questions rely on. The switch
is read on every call, so it needs no restart.

The rules engine is untouched. Its own loaders still return only the original data; the tools, matching,
server and assistant import their loaders from here.
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
    """The 12 brand stores when the brand offers are on, otherwise the six original stores."""
    return _brand_data("brand_stores.json") if brand_offers_on(environ) else engine.load_stores()


def load_offers(environ: Mapping[str, str] | None = None) -> list:
    """The brand offers when the brand offers are on, otherwise the original offers."""
    return _brand_data("brand_offers.json") if brand_offers_on(environ) else engine.load_offers()
