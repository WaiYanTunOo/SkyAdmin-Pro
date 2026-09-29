"""Data-first SkyAgent answer router: SQLite → BM25 RAG → miss."""

from __future__ import annotations

import re
from typing import Any, Protocol

MISS = "No matching data found in SkyAdmin"
_PENDING = re.compile(r"\bpending\b", re.I)
_OVERDUE = re.compile(r"\boverdue\b", re.I)
_TASKS = re.compile(r"\b(?:tasks?|todos?)\b", re.I)
_DOCS = re.compile(r"\b(?:documents?|docs?|invoices?)\b", re.I)


class _LLMLike(Protocol):
    def health_check(self) -> bool: ...

    def summarize(self, documents: str, *, question: str) -> str: ...


def answer(query: str, db: Any, rag: Any, llm: _LLMLike | None = None) -> str:
    """Search DB then RAG; refine online only when local context exists."""
    q = (query or "").strip()
    if not q:
        return MISS
    rows = _search_db(db, q)
    if rows:
        context = _format_rows(rows)
        return _maybe_refine(q, context, llm)
    chunks = rag.search(q, top_k=5) if rag is not None else []
    if chunks:
        context = _format_chunks(chunks)
        return _maybe_refine(q, context, llm)
    return MISS


def _search_db(db: Any, query: str) -> list[dict]:
    if _PENDING.search(query):
        return list(db.get_pending_tasks() or [])
    if _OVERDUE.search(query):
        return list(db.get_overdue_documents() or [])
    rows = list(db.search_clients(query) or [])
    if len(rows) == 1:
        cid = rows[0].get("id")
        if cid is not None:
            extra: list[dict] = []
            if _TASKS.search(query) and hasattr(db, "get_client_tasks"):
                extra.extend(db.get_client_tasks(cid) or [])
            if _DOCS.search(query) and hasattr(db, "get_documents_by_client"):
                extra.extend(db.get_documents_by_client(cid) or [])
            if extra:
                return rows + extra
    return rows


def _format_rows(rows: list[dict]) -> str:
    lines: list[str] = []
    for row in rows:
        parts = [f"{k}: {v}" for k, v in row.items() if v is not None and v != ""]
        if parts:
            lines.append("- " + "; ".join(parts))
    return "\n".join(lines) if lines else MISS


def _format_chunks(chunks: list[dict]) -> str:
    lines = []
    for c in chunks:
        src = c.get("source", "doc")
        text = (c.get("text") or "").strip()
        if text:
            lines.append(f"- [{src}] {text}")
    return "\n".join(lines) if lines else MISS


def _maybe_refine(question: str, context: str, llm: _LLMLike | None) -> str:
    if not context or context == MISS or llm is None:
        return context if context else MISS
    try:
        if not llm.health_check():
            return context
        return llm.summarize(context, question=question)
    except Exception:
        return context
