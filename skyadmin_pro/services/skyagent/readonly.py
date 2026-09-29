"""Read-only query wrapper for SkyAgent.

Provides safe, read-only database access using the existing Database
connection pool. Enforces SELECT-only queries and redacts secrets by default.
"""

from __future__ import annotations

from typing import Any

from ._sql_validator import validate_no_multiple_statements, validate_select_only


class SkyAgentDB:
    """Read-only facade over the existing Database instance."""

    def __init__(self, db: Any, *, decrypt_secrets: bool = False) -> None:
        self._db = db
        self._decrypt = decrypt_secrets

    def _safe_fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        """Execute a SELECT-only query and return list of dicts."""
        validate_select_only(sql)
        validate_no_multiple_statements(sql)
        with self._db.read_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def _safe_fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        """Execute a SELECT-only query and return one dict or None."""
        upper_sql = sql.upper().rstrip()
        if "LIMIT" not in upper_sql:
            sql = sql.rstrip() + " LIMIT 1"
        result = self._safe_fetch_all(sql, params)
        return result[0] if result else None

    def search_clients(self, query: str, limit: int = 20) -> list[dict]:
        """Search clients by name, contact, or email."""
        sql = """
            SELECT id, name, contact_name, email, status, service_type
            FROM clients
            WHERE deleted_at IS NULL
              AND (name LIKE ? OR contact_name LIKE ? OR email LIKE ?)
            ORDER BY name
            LIMIT ?
        """
        q = f"%{query}%"
        rows = self._safe_fetch_all(sql, (q, q, q, limit))
        return self._redact_fields(rows, {"email"})

    def get_client_tasks(self, client_id: int) -> list[dict]:
        """List tasks for a specific client."""
        sql = """
            SELECT id, title, status, category, due_date
            FROM tasks
            WHERE client_id = ? AND deleted_at IS NULL
            ORDER BY due_date DESC
        """
        return self._safe_fetch_all(sql, (client_id,))

    def get_documents_by_client(self, client_id: int) -> list[dict]:
        """List documents for a specific client."""
        sql = """
            SELECT id, document_type, expiry_date, amount, paid, file_name
            FROM documents
            WHERE client_id = ? AND deleted_at IS NULL
            ORDER BY expiry_date
        """
        return self._safe_fetch_all(sql, (client_id,))

    def get_pending_tasks(self, limit: int = 50) -> list[dict]:
        """List all pending tasks across clients."""
        sql = """
            SELECT t.id, t.title, t.status, t.due_date, c.name AS client_name
            FROM tasks t
            JOIN clients c ON t.client_id = c.id
            WHERE t.status = 'pending' AND t.deleted_at IS NULL AND c.deleted_at IS NULL
            ORDER BY t.due_date
            LIMIT ?
        """
        return self._safe_fetch_all(sql, (limit,))

    def get_overdue_documents(self) -> list[dict]:
        """List documents past their expiry date with unpaid status."""
        sql = """
            SELECT d.id, d.document_type, d.expiry_date, d.amount, c.name AS client_name
            FROM documents d
            JOIN clients c ON d.client_id = c.id
            WHERE d.expiry_date < date('now')
              AND d.paid = 0
              AND d.deleted_at IS NULL AND c.deleted_at IS NULL
            ORDER BY d.expiry_date
        """
        return self._safe_fetch_all(sql)

    def get_client_summary(self, client_id: int) -> dict | None:
        """Return a summary dict for a single client."""
        sql = """
            SELECT id, name, contact_name, email, status, service_type,
                   payment_status, tax_id, created_at
            FROM clients
            WHERE id = ? AND deleted_at IS NULL
        """
        return self._safe_fetch_one(sql, (client_id,))

    def _redact_fields(self, rows: list[dict], fields: set[str]) -> list[dict]:
        """Redact sensitive fields unless decryption is enabled."""
        if self._decrypt:
            return rows
        for row in rows:
            for field in fields:
                if field in row and row[field]:
                    row[field] = "***REDACTED***"
        return rows
