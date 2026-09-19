"""Migration 017 — sync + Drive metadata for documents / financial_documents."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

VERSION = 17
NAME = "documents_sync"

TABLES: tuple[str, ...] = ("documents", "financial_documents")

# Sync identity/clocks + Wave 2a Drive pointer metadata (bytes stay on customer Drive).
COLUMNS: tuple[tuple[str, str], ...] = (
    ("global_id", "global_id TEXT"),
    ("deleted_at", "deleted_at TEXT"),
    ("updated_at", "updated_at TEXT"),
    ("hlc", "hlc TEXT"),
    ("drive_file_id", "drive_file_id TEXT"),
    ("drive_parent_path", "drive_parent_path TEXT"),
    ("content_hash", "content_hash TEXT"),
    ("byte_size", "byte_size INTEGER"),
    ("mime_type", "mime_type TEXT"),
    ("original_filename", "original_filename TEXT"),
)

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    with db.connection() as conn:
        for table in TABLES:
            cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            for name, ddl in COLUMNS:
                if name not in cols:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
            if "updated_at" not in cols:
                conn.execute(
                    f"""
                    UPDATE {table}
                    SET updated_at = COALESCE(NULLIF(TRIM(created_at), ''), datetime('now', 'localtime'))
                    WHERE updated_at IS NULL OR TRIM(updated_at) = ''
                    """
                )
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
