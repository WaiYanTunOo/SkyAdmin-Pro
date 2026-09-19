"""Field cleaners for appointments mutate."""

from __future__ import annotations


def clean_time(raw: object) -> str | None:
    text = str(raw or "").strip()
    return text[:8] if text else None


def clean_client_id(raw: object) -> int | None:
    """Coerce blank / non-positive client ids to NULL (avoids FK errors)."""
    if raw is None:
        return None
    if isinstance(raw, str) and not raw.strip():
        return None
    try:
        cid = int(raw)
    except (TypeError, ValueError):
        return None
    return cid if cid > 0 else None


def date_from(fields: dict) -> str:
    return str(fields.get("appointment_date") or fields.get("appt_date") or "").strip()[:10]


def time_from(fields: dict) -> object:
    if "appointment_time" in fields:
        return fields.get("appointment_time")
    return fields.get("appt_time")
