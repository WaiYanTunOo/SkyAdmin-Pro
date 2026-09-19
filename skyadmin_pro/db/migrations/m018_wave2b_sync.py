"""Migration 018 — sync columns for Wave 2b web-surface tables."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

VERSION = 18
NAME = "wave2b_sync"

TABLES: tuple[str, ...] = (
    "pipeline_items",
    "suppliers",
    "supplier_payments",
    "supplier_services",
    "courier_logs",
    "client_months",
    "renewal_items",
    "tax_cycle_log",
    "recurring_tasks",
)

COLUMNS: tuple[tuple[str, str], ...] = (
    ("global_id", "global_id TEXT"),
    ("deleted_at", "deleted_at TEXT"),
    ("updated_at", "updated_at TEXT"),
    ("hlc", "hlc TEXT"),
)

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def _stamp_expr(table: str) -> str:
    if table == "tax_cycle_log":
        return "COALESCE(NULLIF(TRIM(changed_at), ''), datetime('now', 'localtime'))"
    return "COALESCE(NULLIF(TRIM(created_at), ''), datetime('now', 'localtime'))"


def upgrade(db: CoreMixin) -> None:
    with db.connection() as conn:
        for table in TABLES:
            cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            for name, ddl in COLUMNS:
                if name not in cols:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
            if "updated_at" not in cols:
                conn.execute(
                    f"UPDATE {table} SET updated_at = {_stamp_expr(table)} "
                    f"WHERE updated_at IS NULL OR TRIM(updated_at) = ''"
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
