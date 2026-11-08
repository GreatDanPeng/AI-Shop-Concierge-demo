"""A tiny .env loader (standard library only, so no new dependency).

Rules:
- Variables that are already set in the real environment are never overridden.
- Empty values are treated as "not set".
- Values are never printed or logged: only the number of variables loaded is logged.
- It is called explicitly (server start, scripts), never at import time, so importing the
  app in tests cannot pick up a real key.
"""
from __future__ import annotations

import logging
import os
import re
from collections.abc import MutableMapping
from pathlib import Path

log = logging.getLogger("concierge")

DEFAULT_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"  # the project root, not the CWD

_KEY = re.compile(r"[A-Za-z_]\w*", re.ASCII)  # ASCII only: \w must not match accented letters
_INLINE_COMMENT = re.compile(r"\s#")


def _parse_value(raw: str) -> str:
    raw = raw.strip()
    if raw[:1] in ("'", '"'):
        end = raw.find(raw[0], 1)
        rest = raw[end + 1:].strip() if end != -1 else None
        if rest is not None and (rest == "" or rest.startswith("#")):
            return raw[1:end]  # quoted: keep the inside exactly, spaces and # included
    comment = _INLINE_COMMENT.search(raw)
    return (raw[:comment.start()] if comment else raw).strip()


def parse_env(text: str) -> dict[str, str]:
    """KEY=VALUE lines to a dict. Comments, blank lines and malformed lines are skipped."""
    values: dict[str, str] = {}
    for line in text.lstrip("﻿").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, separator, value = line.partition("=")
        key = key.strip()
        if separator and _KEY.fullmatch(key):
            values[key] = _parse_value(value)
    return values


def load_env_file(path: str | os.PathLike | None = None, *,
                  environ: MutableMapping[str, str] | None = None) -> list[str]:
    """Load a .env file into the environment; return the names that were newly set.

    A missing file is fine (returns []). Existing non-blank variables win over the file.
    """
    env = os.environ if environ is None else environ
    target = DEFAULT_ENV_PATH if path is None else Path(path)
    try:
        text = target.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return []
    except (OSError, UnicodeDecodeError) as exc:
        # A damaged .env must not stop the server: matching works without the model. Log the error
        # class only, never any content.
        log.warning("could not read the .env file (%s); using the real environment only",
                    type(exc).__name__)
        return []
    loaded = []
    for key, value in parse_env(text).items():
        if not value.strip() or env.get(key, "").strip():
            continue
        env[key] = value
        loaded.append(key)
    log.info("loaded %d variable(s) from the .env file", len(loaded))
    return loaded
