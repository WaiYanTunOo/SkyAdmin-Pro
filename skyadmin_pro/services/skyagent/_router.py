"""Data-first SkyAgent answer router: SQLite → BM25 RAG → miss."""

from __future__ import annotations

import re
from typing import Any, Protocol

from ._format import MISS, filter_rows_by_query, format_chunks, format_rows

__all__ = ["MISS", "answer"]

_PENDING = re.compile(r"\bpending\b", re.I)
_OVERDUE = re.compile(r"\boverdue\b", re.I)
_TASKS = re.compile(r"\b(?:tasks?|todos?)\b", re.I)
_DOCS = re.compile(r"\b(?:documents?|docs?|invoices?)\b", re.I)
_DROP = frozenset(
    {
        "pending",
        "overdue",
        "pipeline",
        "service",
        "services",
        "find",
        "show",
        "list",
        "get",
        "the",
        "a",
        "an",
        "for",
        "all",
        "task",
        "tasks",
        "todo",
        "todos",
        "doc",
        "docs",
        "document",
        "documents",
        "invoice",
        "invoices",
        "days",
        "day",
        "left",
        "under",
        "within",
        "expiry",
        "expiring",
        "expires",
        "step",
        "process",
    }
)


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
        return _maybe_refine(q, format_rows(rows), llm)
    chunks = rag.search(q, top_k=5) if rag is not None else []
    if chunks:
        return _maybe_refine(q, format_chunks(chunks), llm)
    return MISS


def _search_db(db: Any, query: str) -> list[dict]:
    if _PENDING.search(query) or re.search(r"\bpipeline\b", query, re.I):
        rows = list(db.get_pending_tasks() or [])
        return filter_rows_by_query(rows, query, drop_words=_DROP)
    if _OVERDUE.search(query):
        rows = list(db.get_overdue_documents() or [])
        return filter_rows_by_query(rows, query, drop_words=_DROP)
    from ._expiring import parse_within_days

    within = parse_within_days(query)
    if within is not None and hasattr(db, "get_expiring_within"):
        rows = list(db.get_expiring_within(within) or [])
        return filter_rows_by_query(rows, query, drop_words=_DROP | {str(within)})
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


def _maybe_refine(question: str, context: str, llm: _LLMLike | None) -> str:
    if not context or context == MISS or llm is None:
        return context if context else MISS
    try:
        if not llm.health_check():
            return context
        return llm.summarize(context, question=question)
    except Exception:
        return context
