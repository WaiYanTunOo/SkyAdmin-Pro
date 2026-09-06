"""Migration 011 — sync columns for client_groups (global_id, updated_at, deleted_at)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

VERSION = 11
NAME = "client_groups_sync"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    with db.connection() as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(client_groups)").fetchall()}
        if "global_id" not in cols:
            conn.execute("ALTER TABLE client_groups ADD COLUMN global_id TEXT")
        if "updated_at" not in cols:
            # SQLite forbids non-constant defaults on ADD COLUMN — backfill after.
            conn.execute("ALTER TABLE client_groups ADD COLUMN updated_at TEXT")
            conn.execute(
                """
                UPDATE client_groups
                SET updated_at = COALESCE(NULLIF(TRIM(created_at), ''), datetime('now', 'localtime'))
                WHERE updated_at IS NULL OR TRIM(updated_at) = ''
                """
            )
        if "deleted_at" not in cols:
            conn.execute("ALTER TABLE client_groups ADD COLUMN deleted_at TEXT")
        rows = conn.execute("SELECT id FROM client_groups WHERE global_id IS NULL OR TRIM(global_id) = ''").fetchall()
        for row in rows:
            conn.execute(
                "UPDATE client_groups SET global_id = ? WHERE id = ?",
                (uuid.uuid4().hex, int(row["id"])),
            )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_client_groups_global_id "
            "ON client_groups(global_id) WHERE global_id IS NOT NULL AND TRIM(global_id) != ''"
        )
