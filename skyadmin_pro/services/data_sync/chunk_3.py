from __future__ import annotations

from ..importer.funcs import Database
from ._common import *
from ._common import (
    _SYNC_IDENT_RE,
    SYNC_ALLOWED_COLUMNS,
    Any,
    logger,
)


def _unique_group_name(db: Database, name: str, global_id: str) -> str:
    """Avoid UNIQUE name collisions when two devices create the same label."""
    cleaned = (name or "").strip() or "Group"
    existing = db._fetch_one(
        "SELECT id, global_id FROM client_groups WHERE name = ? COLLATE NOCASE AND deleted_at IS NULL",
        (cleaned,),
    )
    if not existing:
        return cleaned
    if str(existing.get("global_id") or "") == global_id:
        return cleaned
    short = (global_id or "x")[:6]
    candidate = f"{cleaned} ({short})"
    clash = db._fetch_one(
        "SELECT id FROM client_groups WHERE name = ? COLLATE NOCASE AND deleted_at IS NULL "
        "AND (global_id IS NULL OR global_id != ?)",
        (candidate, global_id),
    )
    if not clash:
        return candidate
    return f"{cleaned} ({global_id[:12]})"


def _filter_sync_row(table: str, row: dict[str, Any]) -> dict[str, Any]:
    allowed = SYNC_ALLOWED_COLUMNS.get(table, frozenset())
    return {k: v for k, v in row.items() if k in allowed}


def _sync_ident(name: str) -> str:
    """Quote allowlisted sync SQL identifiers; reject anything else."""
    text = str(name or "")
    if not _SYNC_IDENT_RE.match(text):
        raise ValueError(f"Refusing sync SQL identifier: {name!r}")
    return f'"{text}"'


def _parse_updated_at(value: str) -> float:
    """Parse updated_at to UTC epoch for LWW; unparseable → 0.0."""
    from datetime import datetime, timezone

    text = str(value or "").strip()
    if not text:
        return 0.0
    normalized = text.replace(" ", "T")
    try:
        if normalized.endswith(("Z", "z")):
            dt = datetime.fromisoformat(normalized[:-1] + "+00:00")
        elif len(normalized) >= 6 and normalized[-3] == ":" and (normalized[-6] in "+-"):
            dt = datetime.fromisoformat(normalized)
        else:
            dt = datetime.fromisoformat(normalized)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).timestamp()
    except ValueError:
        logger.debug("Unparseable updated_at %r; falling back to epoch 0", value)
        return 0.0
