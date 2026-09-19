"""Migration 020 — Dashboard Calendar appointments (local-only v1)."""

from __future__ import annotations

from typing import TYPE_CHECKING

VERSION = 20
NAME = "appointments"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    with db.connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id         INTEGER,
                title             TEXT    NOT NULL,
                appointment_date  TEXT    NOT NULL,
                appointment_time  TEXT,
                location          TEXT,
                notes             TEXT,
                created_at        TEXT    NOT NULL
                    DEFAULT (datetime('now', 'localtime')),
                updated_at        TEXT    NOT NULL
                    DEFAULT (datetime('now', 'localtime')),
                deleted_at        TEXT,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_appointments_date" " ON appointments(appointment_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_appointments_client" " ON appointments(client_id)")
