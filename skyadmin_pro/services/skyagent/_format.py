"""Plain, short SkyAgent answer lines (no raw id/status dumps)."""

from __future__ import annotations

from typing import Any

MISS = "No matching data found in SkyAdmin"
_MAX_LINES = 12
_SKIP = frozenset({"id", "client_id", "status", "paid", "file_name", "file_path", "created_at", "step"})


def format_rows(rows: list[dict]) -> str:
    if not rows:
        return MISS
    lines = [_one_line(r) for r in rows]
    lines = [ln for ln in lines if ln]
    if not lines:
        return MISS
    head = _heading(rows[0], len(lines))
    body = lines[:_MAX_LINES]
    extra = len(lines) - len(body)
    out = head + "\n" + "\n".join(f"• {ln}" for ln in body)
    if extra > 0:
        out += f"\n… and {extra} more"
    return out


def format_chunks(chunks: list[dict]) -> str:
    lines = []
    for c in chunks[:_MAX_LINES]:
        src = c.get("source", "doc")
        text = (c.get("text") or "").strip().replace("\n", " ")
        if len(text) > 160:
            text = text[:157] + "…"
        if text:
            lines.append(f"• [{src}] {text}")
    return "\n".join(lines) if lines else MISS


def filter_rows_by_query(rows: list[dict], query: str, *, drop_words: set[str]) -> list[dict]:
    """Keep rows whose client/service/title matches leftover query words."""
    tokens = [
        t
        for t in "".join(ch if ch.isalnum() else " " for ch in (query or "").lower()).split()
        if t and t not in drop_words and len(t) > 1
    ]
    if not tokens:
        return rows
    kept: list[dict] = []
    for row in rows:
        blob = " ".join(str(v) for v in row.values() if v is not None).lower()
        if all(tok in blob for tok in tokens):
            kept.append(row)
    return kept


def _heading(sample: dict[str, Any], n: int) -> str:
    if "service" in sample and "step_label" in sample:
        return f"{n} service pipeline:"
    if "title" in sample:
        return f"{n} pending task(s):"
    if "days_left" in sample:
        return f"{n} expiring:"
    if "payment_date" in sample and "document_type" in sample:
        return f"{n} overdue:"
    if "name" in sample:
        return f"{n} client(s):"
    return f"{n} result(s):"


def _one_line(row: dict[str, Any]) -> str:
    client = str(row.get("client_name") or row.get("name") or "").strip()
    service = row.get("service")
    step_label = row.get("step_label")
    if service is not None:
        bits = [b for b in (client, str(service), str(step_label or "").strip()) if b]
        return " — ".join(bits)
    title = row.get("title")
    if title:
        return f"{client} — {title}".strip(" —") if client else str(title)
    doc = row.get("document_type")
    days = row.get("days_left")
    if doc is not None and days is not None:
        base = f"{client} — {doc}".strip(" —") if client else str(doc)
        return f"{base} ({days} day(s) left)"
    if doc is not None:
        pay = row.get("payment_date")
        base = f"{client} — {doc}".strip(" —") if client else str(doc)
        return f"{base} (due {pay})" if pay else base
    if client:
        contact = row.get("contact_name")
        return f"{client} · {contact}" if contact else client
    parts = [f"{k} {v}" for k, v in row.items() if k not in _SKIP and v not in (None, "")]
    return " · ".join(parts[:4])
