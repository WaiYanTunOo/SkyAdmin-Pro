"""Helpers for document expiry highlighting on the dashboard."""

from __future__ import annotations

from datetime import date

from skyadmin_pro.config import ANNUAL_DEC31_SERVICE_MARKERS


def days_until(iso_date: str | None) -> int | None:
    if not iso_date:
        return None
    try:
        target = date.fromisoformat(str(iso_date)[:10])
    except ValueError:
        return None
    return (target - date.today()).days


def effective_expiry_date(
    expiry_date: str | None, document_type: str | None = None
) -> str | None:
    """Roll an annual year-end (31 Dec) service's expiry forward to the next
    31 December, so a record dated 2025-12-31 stays active until 2026-12-31."""
    if not expiry_date:
        return expiry_date
    try:
        target = date.fromisoformat(str(expiry_date)[:10])
    except ValueError:
        return expiry_date
    low = (document_type or "").lower()
    if not any(marker.lower() in low for marker in ANNUAL_DEC31_SERVICE_MARKERS):
        return expiry_date
    today = date.today()
    if target > today:
        return expiry_date
    this_dec = date(today.year, 12, 31)
    rolled = this_dec if this_dec > today else date(today.year + 1, 12, 31)
    return rolled.isoformat()


def classify_expiry(days_left: int) -> str:
    """Return a treeview tag for the fixed expiry-alert color bands:
    red at 7 or fewer days left, dark orange at 14 or fewer, yellow at 30
    or fewer, green at 45 or fewer; otherwise empty (no alert)."""
    if days_left <= 7:
        return "red"
    if days_left <= 14:
        return "orange"
    if days_left <= 30:
        return "yellow"
    if days_left <= 45:
        return "green"
    return ""


def expiry_label(days_left: int) -> str:
    if days_left < 0:
        return f"Expired {abs(days_left)} day(s) ago"
    if days_left == 0:
        return "Expires today"
    return f"{days_left} day(s) left"
