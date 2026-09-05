"""Migration 005 — import IRD passwords into client_credentials."""

from __future__ import annotations

from typing import TYPE_CHECKING

VERSION = 5
NAME = "ird_to_client_credentials"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def migrate_ird_to_client_credentials(db: CoreMixin) -> int:
    """Import legacy clients.ird_password into Office Hub RD credentials.

    Also callable after first migrate (Office Hub rollout button).
    """
    from skyadmin_pro.services.secret_fields import encrypt_secret, read_plaintext_for_migration

    migrated = 0
    with db.connection() as conn:
        clients = conn.execute(
            """
            SELECT id, ird_password FROM clients
            WHERE ird_password IS NOT NULL AND TRIM(ird_password) != ''
            """
        ).fetchall()
        for client in clients:
            cid = int(client["id"])
            existing = conn.execute(
                """
                SELECT COUNT(*) AS n FROM client_credentials
                WHERE client_id = ? AND credential_type = 'RD'
                """,
                (cid,),
            ).fetchone()["n"]
            if existing:
                continue
            raw = str(client["ird_password"] or "")
            plain = read_plaintext_for_migration(raw)
            if not plain:
                continue
            conn.execute(
                """
                INSERT INTO client_credentials
                    (client_id, credential_type, username, secret_value, notes, updated_at)
                VALUES (?, 'RD', '', ?, 'Imported from Company Details IRD field', ?)
                """,
                (cid, encrypt_secret(plain), db._now()),
            )
            migrated += 1
    return migrated


def upgrade(db: CoreMixin) -> None:
    migrate_ird_to_client_credentials(db)
