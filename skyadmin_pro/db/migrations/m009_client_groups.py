"""Migration 009 — client_groups table and clients.group_id column."""

from __future__ import annotations

from typing import TYPE_CHECKING

VERSION = 9
NAME = "client_groups"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    with db.connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS client_groups (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                color       TEXT,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            """
        )
        cols = {row[1] for row in conn.execute("PRAGMA table_info(clients)").fetchall()}
        if "group_id" not in cols:
            conn.execute(
                "ALTER TABLE clients ADD COLUMN group_id INTEGER REFERENCES client_groups(id) ON DELETE SET NULL;"
            )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_clients_group ON clients(group_id);")
