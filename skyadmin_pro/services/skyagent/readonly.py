"""Read-only query wrapper for SkyAgent.

Safe SELECT-only access via the Database pool; redacts secrets by default.
"""

from __future__ import annotations

from typing import Any

from ._sql_validator import validate_no_multiple_statements, validate_select_only

_REDACT = frozenset({"email", "tax_id"})


class SkyAgentDB:
    """Read-only facade over the existing Database instance."""

    def __init__(self, db: Any, *, decrypt_secrets: bool = False) -> None:
        self._db = db
        self._decrypt = decrypt_secrets

    def _safe_fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        validate_select_only(sql)
        validate_no_multiple_statements(sql)
        with self._db.read_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def _safe_fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        upper_sql = sql.upper().rstrip()
        if "LIMIT" not in upper_sql:
            sql = sql.rstrip() + " LIMIT 1"
        result = self._safe_fetch_all(sql, params)
        return result[0] if result else None

    def search_clients(self, query: str, limit: int = 20) -> list[dict]:
        sql = """
            SELECT id, name, contact_name, email, status, service_type
            FROM clients
            WHERE deleted_at IS NULL
              AND (name LIKE ? OR contact_name LIKE ? OR email LIKE ?)
            ORDER BY name LIMIT ?
        """
        q = f"%{query}%"
        return self._redact_fields(self._safe_fetch_all(sql, (q, q, q, limit)), _REDACT)

    def get_client_tasks(self, client_id: int) -> list[dict]:
        sql = """
            SELECT id, title, status, category, due_date FROM tasks
            WHERE client_id = ? AND deleted_at IS NULL ORDER BY due_date DESC
        """
        return self._safe_fetch_all(sql, (client_id,))

    def get_documents_by_client(self, client_id: int) -> list[dict]:
        sql = """
            SELECT id, document_type, expiry_date, amount, paid, file_name
            FROM documents WHERE client_id = ? AND deleted_at IS NULL
            ORDER BY expiry_date
        """
        return self._safe_fetch_all(sql, (client_id,))

    def get_pending_tasks(self, limit: int = 50) -> list[dict]:
        sql = """
            SELECT t.id, t.title, t.status, t.due_date, c.name AS client_name
            FROM tasks t
            LEFT JOIN clients c ON c.id = t.client_id AND c.deleted_at IS NULL
            WHERE t.status = 'pending' AND t.deleted_at IS NULL
              AND (c.id IS NULL OR COALESCE(c.status, 'active') != 'inactive')
            ORDER BY t.due_date LIMIT ?
        """
        return self._safe_fetch_all(sql, (limit,))

    def get_overdue_documents(self) -> list[dict]:
        """Unpaid docs past payment_date — mirrors dashboard list_overdue_services."""
        sql = """
            SELECT d.id, d.document_type, d.payment_date, d.amount, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.deleted_at IS NULL AND d.client_id IS NOT NULL
              AND c.deleted_at IS NULL AND COALESCE(c.status, 'active') != 'inactive'
              AND d.payment_date IS NOT NULL AND trim(d.payment_date) != ''
              AND date(d.payment_date) < date('now', 'localtime')
              AND COALESCE(d.paid, 0) = 0
            ORDER BY d.payment_date ASC
        """
        return self._safe_fetch_all(sql)

    def get_client_summary(self, client_id: int) -> dict | None:
        sql = """
            SELECT id, name, contact_name, email, status, service_type,
                   payment_status, tax_id, created_at
            FROM clients WHERE id = ? AND deleted_at IS NULL
        """
        row = self._safe_fetch_one(sql, (client_id,))
        if row is None:
            return None
        return self._redact_fields([row], _REDACT)[0]

    def _redact_fields(self, rows: list[dict], fields: set[str] | frozenset[str]) -> list[dict]:
        if self._decrypt:
            return rows
        for row in rows:
            for field in fields:
                if field in row and row[field]:
                    row[field] = "***REDACTED***"
        return rows
