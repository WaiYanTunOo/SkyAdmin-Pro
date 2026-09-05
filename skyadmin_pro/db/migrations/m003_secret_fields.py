"""Migration 003 — encrypt legacy plaintext IRD passwords."""

from __future__ import annotations

from typing import TYPE_CHECKING

VERSION = 3
NAME = "secret_fields"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    """Encrypt legacy plaintext IRD passwords at rest."""
    from skyadmin_pro.services.secret_fields import encrypt_secret, is_encrypted_secret

    with db.connection() as conn:
        rows = conn.execute(
            """
            SELECT id, ird_password
            FROM clients
            WHERE ird_password IS NOT NULL AND TRIM(ird_password) != ''
            """
        ).fetchall()
        for row in rows:
            raw = str(row["ird_password"] or "")
            if raw and not is_encrypted_secret(raw):
                conn.execute(
                    "UPDATE clients SET ird_password = ? WHERE id = ?",
                    (encrypt_secret(raw), int(row["id"])),
                )
