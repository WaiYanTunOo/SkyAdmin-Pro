"""Expiring-document helpers for SkyAgent (Companies → Expiry style)."""

from __future__ import annotations

import re
from typing import Any

from skyadmin_pro.config import EXPIRY_ALERT_DAYS
from skyadmin_pro.services.tracking import days_until, effective_expiry_date, expiry_default_sort_key

# "under 30 days left", "within 45 days", "less than 14 days", "30 days left"
_WITHIN = re.compile(
    r"(?:under|within|less\s+than|in)\s+(\d+)\s+days?" r"|(\d+)\s+days?\s+left" r"|\bexpir(?:y|ing|es)?\b",
    re.I,
)


def parse_within_days(query: str) -> int | None:
    """Return day window from natural language, or None if not an expiry ask."""
    m = _WITHIN.search(query or "")
    if not m:
        return None
    for g in m.groups():
        if g is not None and str(g).isdigit():
            return max(0, int(g))
    # bare "expiry" / "expiring" → same window as Expiry tab alerts
    return int(EXPIRY_ALERT_DAYS)


def filter_expiring_rows(rows: list[dict], within_days: int) -> list[dict]:
    """Keep rows with 0 <= effective days_left <= within_days; sort like Expiry tab."""
    out: list[dict] = []
    for row in rows:
        effective = effective_expiry_date(row.get("expiry_date"), row.get("document_type"))
        left = days_until(effective)
        if left is None or left < 0 or left > within_days:
            continue
        item = dict(row)
        item["days_left"] = left
        out.append(item)
    out.sort(key=lambda r: expiry_default_sort_key(r.get("days_left")))
    return out


def query_expiring_within(db: Any, within_days: int) -> list[dict]:
    """Prefer Database.list_expiring_documents; filter to the requested window."""
    list_fn = getattr(db, "list_expiring_documents", None)
    if not callable(list_fn):
        return []
    rows = list_fn(exclude_expired=True)
    return filter_expiring_rows(list(rows or []), within_days)
