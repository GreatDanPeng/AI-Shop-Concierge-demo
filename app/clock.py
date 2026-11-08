"""The "as of" date the demo uses: the real calendar date, unless CONCIERGE_TODAY pins it.

Pinning (YYYY-MM-DD) is for repeatable demos, evals and tests. A bad value is ignored, with a
warning that names the setting but never prints what it held. It is the server's local date.

The rules engine keeps its own fixed DEMO_TODAY as a default argument (its starter tests rely on
it); the server and the assistant loop call today() and pass the date down explicitly.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import date
from typing import Callable, Mapping

log = logging.getLogger(__name__)

PIN_VARIABLE = "CONCIERGE_TODAY"
_ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")  # ASCII digits only; no other ISO forms


def today(environ: Mapping[str, str] | None = None, *, real: Callable[[], date] = date.today) -> date:
    """The pinned date if CONCIERGE_TODAY holds a valid one, otherwise the real date."""
    environ = os.environ if environ is None else environ
    pin = environ.get(PIN_VARIABLE, "").strip()
    if not pin:
        return real()
    if _ISO_DATE.fullmatch(pin):
        try:
            return date.fromisoformat(pin)
        except ValueError:
            pass
    log.warning("%s is not a valid YYYY-MM-DD date; using the real date", PIN_VARIABLE)
    return real()
