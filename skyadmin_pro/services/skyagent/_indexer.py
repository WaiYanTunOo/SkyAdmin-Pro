"""Document folder indexing for SkyAgent RAG."""

from __future__ import annotations

from pathlib import Path

from .rag import RAGIndex


def index_docs_folder(docs_dir: Path, *, chunk_size: int = 400) -> RAGIndex:
    """Index all .md files in a directory, returning a built RAGIndex."""
    index = RAGIndex()
    documents = []
    if docs_dir.is_dir():
        for md_file in sorted(docs_dir.glob("**/*.md")):
            try:
                text = md_file.read_text(encoding="utf-8", errors="ignore")
                documents.append({"source": md_file.name, "text": text})
            except OSError:
                continue
    index.build(documents, chunk_size=chunk_size)
    return index
