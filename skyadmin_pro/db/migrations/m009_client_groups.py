"""Add client_groups table and group_id FK to clients."""

from __future__ import annotations

SCHEMA_VERSION = 9

MIGRATION_SQL = [
    """
    CREATE TABLE IF NOT EXISTS client_groups (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT    NOT NULL UNIQUE COLLATE NOCASE,
        color       TEXT,
        created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    """,
    "ALTER TABLE clients ADD COLUMN group_id INTEGER REFERENCES client_groups(id) ON DELETE SET NULL;",
    "CREATE INDEX IF NOT EXISTS idx_clients_group ON clients(group_id);",
]


def run(conn) -> None:
    for stmt in MIGRATION_SQL:
        try:
            conn.execute(stmt)
        except Exception:
            pass  # column already exists
