"""Magic Search — one query across local app records (no chat/LLM)."""

from __future__ import annotations

from typing import Any

from skyadmin_pro.config import EXPIRY_ALERT_DAYS

from ._expiry import has_expiry_intent, search_expiry
from ._office import search_contacts, search_courier, search_suppliers
from ._sources import search_clients, search_documents, search_pipeline

__all__ = ["magic_search"]

_TYPE_ORDER = {
    "Client": 0,
    "Expiry": 1,
    "Pipeline": 2,
    "Document": 3,
    "Contact": 4,
    "Supplier": 5,
    "Courier": 6,
}


def _sort_key(hit: dict, q: str) -> tuple:
    title = (hit.get("title") or "").lower()
    return (
        _TYPE_ORDER.get(hit.get("type"), 9),
        0 if q and title.startswith(q) else 1,
        0 if q and q in title else 1,
        title,
    )


def _dedupe(hits: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for hit in hits:
        key = (hit.get("type"), hit.get("title"), hit.get("subtitle"), hit.get("open"))
        if key in seen:
            continue
        seen.add(key)
        out.append(hit)
    return out


def magic_search(db: Any, query: str, *, kind: str = "all") -> list[dict]:
    """Return hits: type, title, subtitle, nav, open."""
    q = (query or "").strip().lower()
    if len(q) < 2:
        return []
    out: list[dict] = []
    want_expiry = kind == "expiry" or (kind == "all" and has_expiry_intent(q))
    if kind in ("all", "clients"):
        out.extend(search_clients(db, q))
    if kind in ("all", "pipeline"):
        out.extend(search_pipeline(db, q))
    if want_expiry:
        out.extend(search_expiry(db, q, default_window=int(EXPIRY_ALERT_DAYS)))
    if kind == "docs" or (kind == "all" and not want_expiry):
        out.extend(search_documents(db, q))
    if kind in ("all", "contacts"):
        out.extend(search_contacts(db, q))
    if kind in ("all", "suppliers"):
        out.extend(search_suppliers(db, q))
    if kind in ("all", "courier"):
        out.extend(search_courier(db, q))
    out = [h for h in out if (h.get("title") or "").strip()]
    out = _dedupe(out)
    out.sort(key=lambda h: _sort_key(h, q))
    return out[:80]
