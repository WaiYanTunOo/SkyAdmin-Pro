"""Expiry-focused Magic Search (Companies → Expiry tab)."""

from __future__ import annotations

import re
from typing import Any

from skyadmin_pro.config import EXPIRY_ALERT_DAYS
from skyadmin_pro.services.tracking import (
    days_left_label,
    days_until,
    effective_expiry_date,
    expiry_default_sort_key,
    expiry_label,
)

from ._sources import _PER, _rows, match

_WITHIN = re.compile(
    r"(?:under|within|less\s+than|in)\s+(\d+)\s+days?" r"|(\d+)\s+days?\s+left" r"|\bexpir(?:y|ing|es|ed)?\b",
    re.I,
)
_DROP = frozenset(
    "under within less than in days day left expiry expiring expires expired " "find show list due soon near".split()
)


def has_expiry_intent(q: str) -> bool:
    return bool(_WITHIN.search(q or ""))


def _window_days(q: str) -> int | None:
    m = _WITHIN.search(q or "")
    if not m:
        return None
    for g in m.groups():
        if g is not None and str(g).isdigit():
            return max(0, int(g))
    return int(EXPIRY_ALERT_DAYS)


def _text_tokens(q: str) -> list[str]:
    return [
        t
        for t in "".join(ch if ch.isalnum() else " " for ch in (q or "").lower()).split()
        if t and t not in _DROP and not t.isdigit() and len(t) > 1
    ]


def search_expiry(db: Any, q: str, *, default_window: int | None = None) -> list[dict]:
    """Companies → Expiry hits with days left. default_window when filter=Expiry."""
    window = _window_days(q)
    if window is None and default_window is not None:
        window = default_window
    tokens = _text_tokens(q)
    if window is None and not tokens:
        return []
    scored: list[tuple[tuple[int, int], dict]] = []
    for row in _rows(getattr(db, "list_documents", None), limit=800):
        dtype, client = row.get("document_type") or "", row.get("client_name") or ""
        effective = effective_expiry_date(row.get("expiry_date"), dtype)
        left = days_until(effective)
        if left is None:
            continue
        if window is not None and left > window:
            continue
        if tokens and not match(" ".join(tokens), client, dtype, row.get("file_name"), effective):
            continue
        scored.append(
            (
                expiry_default_sort_key(left),
                {
                    "type": "Expiry",
                    "title": f"{client} — {dtype}" if client else dtype,
                    "subtitle": f"{days_left_label(left)} · {expiry_label(left)}",
                    "nav": "database_tasks",
                    "open": ("expiry", client),
                },
            )
        )
    scored.sort(key=lambda x: x[0])
    return [item for _, item in scored[:_PER]]
