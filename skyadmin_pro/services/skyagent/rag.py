"""Simple BM25-based RAG for SkyAgent document retrieval."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from ._bm25 import bm25_score, tokenize


class RAGIndex:
    """BM25 index over a collection of text chunks."""

    def __init__(self) -> None:
        self._chunks: list[dict[str, Any]] = []
        self._chunk_tokens: list[list[str]] = []
        self._idf: dict[str, float] = {}
        self._avg_dl: float = 0.0

    def build(self, documents: list[dict[str, str]], *, chunk_size: int = 400) -> None:
        """Build index from documents.

        Each document: {"source": "filename", "text": "content"}.
        Chunking splits on double-newlines (paragraphs) up to chunk_size tokens.
        """
        self._chunks.clear()
        self._chunk_tokens.clear()
        for doc in documents:
            source = doc.get("source", "unknown")
            paragraphs = doc.get("text", "").split("\n\n")
            chunk_text = ""
            for para in paragraphs:
                if len(tokenize(chunk_text + para)) > chunk_size and chunk_text:
                    self._chunks.append({"source": source, "text": chunk_text.strip()})
                    chunk_text = para
                else:
                    chunk_text += "\n\n" + para if chunk_text else para
            if chunk_text.strip():
                self._chunks.append({"source": source, "text": chunk_text.strip()})

        n_docs = len(self._chunks)
        if n_docs == 0:
            return
        df: dict[str, int] = {}
        dl_sum = 0
        for chunk in self._chunks:
            tokens = tokenize(chunk["text"])
            self._chunk_tokens.append(tokens)
            dl_sum += len(tokens)
            for t in set(tokens):
                df[t] = df.get(t, 0) + 1
        self._avg_dl = dl_sum / n_docs
        self._idf = {t: math.log((n_docs - c + 0.5) / (c + 0.5) + 1) for t, c in df.items()}

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Return top-k chunks ranked by BM25 score."""
        if not self._chunks:
            return []
        query_tokens = tokenize(query)
        scored = []
        for i, chunk in enumerate(self._chunks):
            score = bm25_score(query_tokens, self._chunk_tokens[i], self._avg_dl, self._idf)
            if score > 0:
                scored.append((score, i, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"source": c["source"], "text": c["text"], "score": round(s, 4)} for s, _, c in scored[:top_k]]

    def save(self, path: Path) -> None:
        """Persist index to JSON."""
        data = {
            "chunks": self._chunks,
            "chunk_tokens": self._chunk_tokens,
            "idf": self._idf,
            "avg_dl": self._avg_dl,
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def load(self, path: Path) -> bool:
        """Load index from JSON. Returns False if file missing or corrupt."""
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            chunks = data["chunks"]
            chunk_tokens = data.get("chunk_tokens", [])
            idf = data["idf"]
            avg_dl = data["avg_dl"]
            if not isinstance(chunks, list) or not isinstance(idf, dict) or not isinstance(avg_dl, int | float):
                return False
            if not isinstance(chunk_tokens, list):
                return False
            self._chunks = chunks
            self._chunk_tokens = chunk_tokens
            self._idf = idf
            self._avg_dl = avg_dl
            return True
        except (json.JSONDecodeError, KeyError, TypeError):
            return False

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)
