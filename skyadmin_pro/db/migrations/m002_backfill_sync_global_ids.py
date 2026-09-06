"""Migration 002 — assign sync global_id UUIDs."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from skyadmin_pro.db.cipher import DB_ERRORS

VERSION = 2
NAME = "backfill_sync_global_ids"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    """Assign stable global_id UUIDs for P4 sync."""
    # Local import: core imports this package inside _initialize.
    from skyadmin_pro.db.core import CoreMixin

    with db.connection() as conn:
        fts_exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='clients_fts'").fetchone()
        if fts_exists:
            CoreMixin._drop_clients_fts_triggers(conn)
        for table in ("clients", "tasks", "office_contacts", "notebook_entries"):
            rows = conn.execute(f"SELECT id FROM {table} WHERE global_id IS NULL OR TRIM(global_id) = ''").fetchall()
            for row in rows:
                conn.execute(
                    f"UPDATE {table} SET global_id = ? WHERE id = ?",
                    (uuid.uuid4().hex, int(row["id"])),
                )
        if fts_exists:
            CoreMixin._ensure_clients_fts_triggers(conn)
            try:
                conn.execute("INSERT INTO clients_fts(clients_fts) VALUES('rebuild')")
            except DB_ERRORS:
                db._log.warning("clients_fts rebuild after backfill failed", exc_info=True)
