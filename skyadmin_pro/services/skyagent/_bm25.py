"""BM25 scoring helpers for SkyAgent RAG."""

from __future__ import annotations

import re


def tokenize(text: str) -> list[str]:
    """Lowercase split on non-alphanumeric; drops tokens < 2 chars."""
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) >= 2]


def bm25_score(
    query_tokens: list[str],
    doc_tokens: list[str],
    avg_dl: float,
    idf: dict[str, float],
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """Compute BM25 score for a query against a document."""
    dl = len(doc_tokens)
    tf_map: dict[str, int] = {}
    for t in doc_tokens:
        tf_map[t] = tf_map.get(t, 0) + 1
    score = 0.0
    for qt in query_tokens:
        if qt not in idf:
            continue
        tf = tf_map.get(qt, 0)
        norm = 1 - b + b * (dl / avg_dl)
        score += idf[qt] * (tf * (k1 + 1)) / (tf + k1 * norm)
    return score
