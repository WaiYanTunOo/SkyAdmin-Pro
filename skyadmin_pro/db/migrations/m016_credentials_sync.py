"""Migration 016 — sync columns for client/office credentials (Wave E)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

VERSION = 16
NAME = "credentials_sync"

TABLES: tuple[str, ...] = ("client_credentials", "office_credentials")

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    with db.connection() as conn:
        for table in TABLES:
            cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            if "global_id" not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN global_id TEXT")
            if "deleted_at" not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN deleted_at TEXT")
            if "hlc" not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN hlc TEXT")
            rows = conn.execute(f"SELECT id FROM {table} WHERE global_id IS NULL OR TRIM(global_id) = ''").fetchall()
            for row in rows:
                conn.execute(
                    f"UPDATE {table} SET global_id = ? WHERE id = ?",
                    (uuid.uuid4().hex, int(row["id"])),
                )
            conn.execute(
                f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{table}_global_id "
                f"ON {table}(global_id) WHERE global_id IS NOT NULL AND TRIM(global_id) != ''"
            )
