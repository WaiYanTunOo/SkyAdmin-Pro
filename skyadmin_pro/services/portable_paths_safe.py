"""Containment helpers: document paths must resolve under the workspace root."""

from __future__ import annotations

from pathlib import Path


def resolve_file_under_root(root: Path, raw: str) -> Path | None:
    """Return the file if *raw* resolves to a real file under *root*; else None."""
    text = (raw or "").strip()
    if not text:
        return None
    base = root.resolve()
    p = Path(text)
    try:
        candidate = p.resolve() if p.is_absolute() else (base / p).resolve()
    except OSError:
        return None
    try:
        if not candidate.is_relative_to(base):
            return None
    except (OSError, ValueError):
        return None
    return candidate if candidate.is_file() else None


def relpath_under_root(root: Path, path: Path) -> str | None:
    """POSIX path relative to *root*, or None if *path* escapes."""
    base = root.resolve()
    try:
        resolved = path.resolve()
        if not resolved.is_relative_to(base):
            return None
        return resolved.relative_to(base).as_posix()
    except (OSError, ValueError):
        return None
