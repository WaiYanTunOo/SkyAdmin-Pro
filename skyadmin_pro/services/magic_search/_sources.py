"""Core Magic Search collectors (clients, pipeline, documents)."""

from __future__ import annotations

from typing import Any

from skyadmin_pro.config import PIPELINE_STEPS

_PER = 25


def match(q: str, *parts: object) -> bool:
    blob = " ".join(str(p) for p in parts if p).lower()
    return all(tok in blob for tok in q.split() if tok)


def _rows(fn: Any, *args: Any, **kwargs: Any) -> list:
    if not callable(fn):
        return []
    try:
        return list(fn(*args, **kwargs) or [])
    except TypeError:
        try:
            return list(fn(*args) or [])
        except Exception:
            return []
    except Exception:
        return []


def search_clients(db: Any, q: str) -> list[dict]:
    rows = _rows(getattr(db, "search_clients", None), q, limit=_PER)
    if not rows:
        rows = _rows(getattr(db, "search_clients", None), q)[:_PER]
    return [
        {
            "type": "Client",
            "title": row.get("name") or "",
            "subtitle": row.get("contact_name") or row.get("email") or row.get("status") or "",
            "nav": "database_tasks",
            "open": ("company", row.get("name") or ""),
        }
        for row in rows
    ]


def search_pipeline(db: Any, q: str) -> list[dict]:
    hits: list[dict] = []
    for row in _rows(getattr(db, "list_pipeline_items", None), limit=500):
        step = int(row.get("step") or 0)
        label = PIPELINE_STEPS[step - 1] if 1 <= step <= len(PIPELINE_STEPS) else f"Step {step}"
        client, service = row.get("client_name") or "", row.get("service") or ""
        if not match(q, client, service, label, row.get("notes")):
            continue
        hits.append(
            {
                "type": "Pipeline",
                "title": f"{client} — {service}" if client else service,
                "subtitle": label,
                "nav": "pipeline",
                "open": ("pipeline", row.get("id")),
            }
        )
        if len(hits) >= _PER:
            break
    return hits


def search_documents(db: Any, q: str) -> list[dict]:
    hits: list[dict] = []
    for row in _rows(getattr(db, "list_documents", None), limit=800):
        name = row.get("file_name") or row.get("document_type") or ""
        client, dtype = row.get("client_name") or "", row.get("document_type") or ""
        if not match(q, name, client, dtype, row.get("expiry_date")):
            continue
        hits.append(
            {
                "type": "Document",
                "title": name,
                "subtitle": f"{dtype} — {client}".strip(" —"),
                "nav": "database_tasks",
                "open": ("company", client) if client else ("expiry", None),
            }
        )
        if len(hits) >= _PER:
            break
    return hits
