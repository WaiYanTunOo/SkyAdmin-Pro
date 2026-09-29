"""Office-side Magic Search collectors (contacts, suppliers, courier)."""

from __future__ import annotations

from typing import Any

from ._sources import _PER, _rows, match


def search_contacts(db: Any, q: str) -> list[dict]:
    hits: list[dict] = []
    for row in _rows(getattr(db, "list_office_contacts", None)):
        name, org = row.get("name") or "", row.get("organization") or ""
        if not match(q, name, org, row.get("role_title"), row.get("email")):
            continue
        hits.append(
            {
                "type": "Contact",
                "title": name,
                "subtitle": row.get("role_title") or org,
                "nav": "office_hub",
                "open": ("office", None),
            }
        )
        if len(hits) >= _PER:
            break
    return hits


def search_suppliers(db: Any, q: str) -> list[dict]:
    hits: list[dict] = []
    for row in _rows(getattr(db, "list_suppliers", None), limit=400):
        name = row.get("name") or row.get("company_name") or ""
        if not match(q, name, row.get("service_type"), row.get("contact_name"), row.get("email")):
            continue
        hits.append(
            {
                "type": "Supplier",
                "title": name,
                "subtitle": row.get("service_type") or row.get("contact_name") or "",
                "nav": "suppliers",
                "open": ("suppliers", None),
            }
        )
        if len(hits) >= _PER:
            break
    return hits


def search_courier(db: Any, q: str) -> list[dict]:
    hits: list[dict] = []
    for row in _rows(getattr(db, "list_courier_logs", None), limit=400):
        tracking, client = row.get("tracking_number") or "", row.get("client_name") or ""
        if not match(q, tracking, client, row.get("driver_name"), row.get("destination")):
            continue
        hits.append(
            {
                "type": "Courier",
                "title": tracking or client or "Courier",
                "subtitle": f"{client} — {row.get('destination') or ''}".strip(" —"),
                "nav": "courier",
                "open": ("courier", None),
            }
        )
        if len(hits) >= _PER:
            break
    return hits
