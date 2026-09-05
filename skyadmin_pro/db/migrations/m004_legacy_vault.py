"""Migration 004 — move vault_entries into credential tables."""

from __future__ import annotations

from typing import TYPE_CHECKING

VERSION = 4
NAME = "legacy_vault"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    """Move legacy vault_entries rows into client_credentials / office_credentials."""
    with db.connection() as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "vault_entries" not in tables:
            return
        rows = conn.execute("SELECT * FROM vault_entries").fetchall()
        if not rows:
            return
        for row in rows:
            data = dict(row)
            secret = data.get("secret_value") or ""
            if data.get("client_id"):
                conn.execute(
                    """
                    INSERT INTO client_credentials
                        (client_id, credential_type, registration_number, username,
                         secret_value, portal_url, notes, is_favorite, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data["client_id"],
                        data.get("category") or "Other",
                        data.get("title"),
                        data.get("username"),
                        secret,
                        data.get("url"),
                        data.get("notes"),
                        data.get("is_favorite") or 0,
                        db._now(),
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO office_credentials
                        (account_label, login_id, email, secret_value, system_type,
                         portal_url, contact_id, notes, is_favorite, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data.get("title") or "Office account",
                        data.get("username"),
                        data.get("username"),
                        secret,
                        data.get("category") or "Email",
                        data.get("url"),
                        data.get("contact_id"),
                        data.get("notes"),
                        data.get("is_favorite") or 0,
                        db._now(),
                    ),
                )
        conn.execute("DELETE FROM vault_entries")
