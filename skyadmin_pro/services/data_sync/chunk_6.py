from __future__ import annotations

from ..importer.funcs import Database
from ._common import *
from ._common import SYNC_PUSH_ORDER, SYNC_TABLES, Any
from .chunk_3 import _sync_ident
from .chunk_5 import _apply_remote_change


def apply_remote_changes(db: Database, changes: list[dict[str, Any]]) -> tuple[int, int]:
    applied = 0
    conflicts = 0
    deletes = [c for c in changes if c.get("deleted_at")]
    upserts = [c for c in changes if not c.get("deleted_at")]
    deletes_ordered = sorted(
        deletes, key=lambda c: -(SYNC_PUSH_ORDER.index(c["table"]) if c.get("table") in SYNC_PUSH_ORDER else -99)
    )
    upserts_ordered = sorted(
        upserts, key=lambda c: SYNC_PUSH_ORDER.index(c["table"]) if c.get("table") in SYNC_PUSH_ORDER else 99
    )
    opener = getattr(db, "bundle_queries", None) or db.connection
    with opener():
        for change in deletes_ordered + upserts_ordered:
            result = _apply_remote_change(db, change)
            if result == "applied":
                applied += 1
            elif result == "skipped":
                conflicts += 1
    return (applied, conflicts)


def ensure_sync_ids(db: Database) -> None:
    """Assign global_id to any rows missing one before push."""
    import uuid

    with db.connection() as conn:
        for table in SYNC_TABLES:
            t = _sync_ident(table)
            rows = conn.execute(f"SELECT id FROM {t} WHERE global_id IS NULL OR TRIM(global_id) = ''").fetchall()
            for row in rows:
                conn.execute(f"UPDATE {t} SET global_id = ? WHERE id = ?", (uuid.uuid4().hex, int(row["id"])))
