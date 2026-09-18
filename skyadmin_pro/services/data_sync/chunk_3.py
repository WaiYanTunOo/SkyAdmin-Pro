from __future__ import annotations

from ..importer.funcs import Database
from ._common import *
from ._common import (
    _SYNC_IDENT_RE,
    FK_CLIENT_COLUMN,
    FK_GROUP_COLUMN,
    SYNC_ALLOWED_COLUMNS,
    SYNC_EXCLUDED_COLUMNS,
    Any,
    logger,
)
from .chunk_2 import _client_global_id


def _unique_group_name(db: Database, name: str, global_id: str) -> str:
    """Avoid UNIQUE name collisions when two devices create the same label."""
    cleaned = (name or "").strip() or "Group"
    existing = db._fetch_one(
        "\n        SELECT id, global_id FROM client_groups\n        WHERE name = ? COLLATE NOCASE AND deleted_at IS NULL\n        ",
        (cleaned,),
    )
    if not existing:
        return cleaned
    if str(existing.get("global_id") or "") == global_id:
        return cleaned
    short = (global_id or "x")[:6]
    candidate = f"{cleaned} ({short})"
    clash = db._fetch_one(
        "\n        SELECT id FROM client_groups\n        WHERE name = ? COLLATE NOCASE AND deleted_at IS NULL\n          AND (global_id IS NULL OR global_id != ?)\n        ",
        (candidate, global_id),
    )
    if not clash:
        return candidate
    return f"{cleaned} ({global_id[:12]})"


def _filter_sync_row(table: str, row: dict[str, Any]) -> dict[str, Any]:
    allowed = SYNC_ALLOWED_COLUMNS.get(table, frozenset())
    return {k: v for k, v in row.items() if k in allowed}


def _sync_ident(name: str) -> str:
    """Quote a table/column identifier for sync SQL.

    Trust assumption: every identifier passed here is an allowlisted constant —
    table names are validated against SYNC_TABLES and column names originate
    from SYNC_ALLOWED_COLUMNS (plus the internal remaps ``global_id``,
    ``updated_at``, ``client_id``, ``group_id``). Remote payload keys are
    filtered through _filter_sync_row before reaching SQL. Quoting is
    defense-in-depth; anything outside ``[A-Za-z_][A-Za-z0-9_]*`` raises.
    """
    text = str(name or "")
    if not _SYNC_IDENT_RE.match(text):
        raise ValueError(f"Refusing sync SQL identifier: {name!r}")
    return f'"{text}"'


def _parse_updated_at(value: str) -> float:
    """Parse an `updated_at` value to a UTC epoch for last-write-wins.

    Fleet convention: desktop writers stamp local-naive
    ``YYYY-MM-DD HH:MM:SS`` (``Database._now()`` / ``datetime('now',
    'localtime')``). Naive values are treated as UTC so ordering stays
    consistent across rows sharing the convention; values carrying an
    explicit zone (``Z`` or ``±HH:MM``) are honored exactly.
    Unparseable input returns 0.0 (loses LWW) instead of raising.
    """
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


def _row_to_sync_payload(db: Database, table: str, row: dict) -> dict[str, Any]:
    payload = dict(row)
    for col in SYNC_EXCLUDED_COLUMNS.get(table, frozenset()):
        payload.pop(col, None)
    if table in ("tasks", "office_contacts", "notebook_entries"):
        payload[FK_CLIENT_COLUMN] = _client_global_id(db, row.get("client_id"))
        payload.pop("client_id", None)
    if table == "clients":
        gid = row.get("group_id")
        if gid is not None:
            g_row = db._fetch_one(
                "SELECT global_id FROM client_groups WHERE id = ? AND deleted_at IS NULL", (int(gid),)
            )
            payload[FK_GROUP_COLUMN] = str(g_row["global_id"]) if g_row and g_row.get("global_id") else None
        else:
            payload[FK_GROUP_COLUMN] = None
        payload.pop("group_id", None)
    payload["global_id"] = str(row.get("global_id") or "")
    return payload
