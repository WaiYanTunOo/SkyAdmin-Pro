"""Database Clients operations."""

from __future__ import annotations

from datetime import datetime


class CrudMixinA:
    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def list_clients(self, *, limit: int | None = None, offset: int = 0) -> list[dict]:
        base = """
            SELECT id, name, company_name, contact_name, email, status, notes,
                   registration_number, director, contact_number,
                   registered_capital, vat_registration, business_address,
                   business_objectives, group_id, created_at, updated_at
            FROM clients
            WHERE deleted_at IS NULL
            ORDER BY name COLLATE NOCASE
            """
        if limit is not None and int(limit) > 0:
            return self._fetch_page(base, (), limit=limit, offset=offset)
        return self._fetch_all(base)

    def count_clients(self, query: str = "") -> int:
        q = (query or "").strip()
        if not q:
            row = self._fetch_one("SELECT COUNT(*) AS n FROM clients WHERE deleted_at IS NULL")
            return int(row["n"]) if row else 0
        # LIKE fallback count (FTS count would need MATCH sync; LIKE is safe).
        from skyadmin_pro.db.sql_helpers import _escape_like as _esc

        like = f"%{_esc(q)}%"
        row = self._fetch_one(
            "SELECT COUNT(*) AS n FROM clients"
            " WHERE deleted_at IS NULL"
            " AND (name LIKE ? ESCAPE '\\' OR contact_name LIKE ? ESCAPE '\\'"
            " OR email LIKE ? ESCAPE '\\')",
            (like, like, like),
        )
        return int(row["n"]) if row else 0

    def get_client(self, client_id: int) -> dict | None:
        row = self._fetch_one(
            "SELECT * FROM clients WHERE id = ?",
            (client_id,),
        )
        return self._prepare_client_record(row)
