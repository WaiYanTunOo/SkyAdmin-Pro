"""SQL helper utilities for the database layer."""

from __future__ import annotations

from datetime import date

from skyadmin_pro.config import EXPIRY_ALERT_DAYS


def _in_clause(column: str, values: tuple[str, ...]) -> tuple[str, list]:
    placeholders = ", ".join("?" for _ in values)
    return f"{column} IN ({placeholders})", list(values)


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards so user text matches literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _expiry_type_condition(column: str, types: tuple[str, ...]) -> str:
    clauses = []
    for name in (*types, "License"):
        safe = name.replace("'", "''").replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        clauses.append(f"{column} LIKE '%{safe}%' ESCAPE '\\'")
    return "(" + " OR ".join(clauses) + ")"


def _expiry_window_condition(type_column: str, date_column: str) -> str:
    """Flat expiry-alert window for registered service types."""
    return f"{date_column} <= date('now', 'localtime', '+{int(EXPIRY_ALERT_DAYS)} days')"


def _days_between(start_iso: str, end_iso: str) -> int | None:
    """Whole calendar days between two YYYY-MM-DD strings."""
    try:
        s = date.fromisoformat(start_iso[:10])
        e = date.fromisoformat(end_iso[:10])
    except (ValueError, TypeError):
        return None
    return max(0, (e - s).days)
