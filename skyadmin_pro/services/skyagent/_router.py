"""Data-first SkyAgent answer router: SQLite → BM25 RAG → miss."""

from __future__ import annotations

from typing import Any, Protocol

MISS = "No matching data found in SkyAdmin"


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
    lower = query.lower()
    if "pending" in lower:
        rows = db.get_pending_tasks()
    elif "overdue" in lower:
        rows = db.get_overdue_documents()
    else:
        rows = db.search_clients(query)
    return list(rows or [])


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
    if llm is None:
        return context
    try:
        if not llm.health_check():
            return context
        return llm.summarize(context, question=question)
    except Exception:
        return context
