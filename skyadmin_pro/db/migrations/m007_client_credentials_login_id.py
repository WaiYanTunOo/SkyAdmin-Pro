"""Migration 007 — client_credentials login_id backfill."""

from __future__ import annotations

from typing import TYPE_CHECKING

VERSION = 7
NAME = "client_credentials_login_id"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    with db.connection() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(client_credentials)")}
        if "login_id" not in columns:
            conn.execute("ALTER TABLE client_credentials ADD COLUMN login_id TEXT")
        conn.execute(
            """
            UPDATE client_credentials
            SET login_id = COALESCE(
                NULLIF(TRIM(login_id), ''),
                NULLIF(TRIM(registration_number), ''),
                NULLIF(TRIM(username), '')
            )
            WHERE login_id IS NULL OR TRIM(login_id) = ''
            """
        )
