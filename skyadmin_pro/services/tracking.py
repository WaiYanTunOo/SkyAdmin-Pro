"""Helpers for document expiry highlighting on the dashboard."""

from __future__ import annotations

from datetime import date


def days_until(iso_date: str | None) -> int | None:
    if not iso_date:
        return None
    try:
        target = date.fromisoformat(str(iso_date)[:10])
    except ValueError:
        return None
    return (target - date.today()).days


def classify_expiry(days_left: int) -> str:
    """Return a treeview tag: expired, urgent (≤14 days), or watch (≤45 days)."""
    if days_left < 0:
        return "expired"
    if days_left <= 14:
        return "urgent"
    return "watch"


def expiry_label(days_left: int) -> str:
    if days_left < 0:
        return f"Expired {abs(days_left)} day(s) ago"
    if days_left == 0:
        return "Expires today"
    return f"{days_left} day(s) left"
