"""Database Core operations."""

from __future__ import annotations

from skyadmin_pro.db.cipher import (
    DBConnection,
)


class FtsMixin:
    @staticmethod
    def _drop_clients_fts_triggers(conn: DBConnection) -> None:
        for name in ("clients_fts_ai", "clients_fts_ad", "clients_fts_au"):
            conn.execute(f"DROP TRIGGER IF EXISTS {name}")

    @staticmethod
    @staticmethod
    def _ensure_clients_fts_triggers(conn: DBConnection) -> None:
        FtsMixin._drop_clients_fts_triggers(conn)
        conn.execute(
            """
            CREATE TRIGGER clients_fts_ai AFTER INSERT ON clients BEGIN
                INSERT INTO clients_fts(rowid, name, contact_name, email)
                VALUES (new.id, COALESCE(new.name,''), COALESCE(new.contact_name,''), COALESCE(new.email,''));
            END
            """
        )
        conn.execute(
            """
            CREATE TRIGGER clients_fts_ad AFTER DELETE ON clients BEGIN
                DELETE FROM clients_fts WHERE rowid = old.id;
            END
            """
        )
        conn.execute(
            """
            CREATE TRIGGER clients_fts_au AFTER UPDATE ON clients BEGIN
                DELETE FROM clients_fts WHERE rowid = old.id;
                INSERT INTO clients_fts(rowid, name, contact_name, email)
                VALUES (new.id, COALESCE(new.name,''), COALESCE(new.contact_name,''), COALESCE(new.email,''));
            END
            """
        )

    @staticmethod
    @staticmethod
    def _prepare_client_record(row: dict | None) -> dict | None:
        if row is None:
            return None
        from skyadmin_pro.services.secret_fields import decrypt_secret

        data = dict(row)
        if "ird_password" in data:
            data["ird_password"] = decrypt_secret(data.get("ird_password"))
        return data
