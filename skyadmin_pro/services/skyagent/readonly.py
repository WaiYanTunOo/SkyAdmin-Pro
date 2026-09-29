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
        import sqlite3

        validate_select_only(sql)
        validate_no_multiple_statements(sql)
        try:
            with self._db.read_connection() as conn:
                rows = conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            return []
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
        """Incomplete Service Pipeline rows (Tasks tab removed from nav)."""
        from skyadmin_pro.config import PIPELINE_MAX_STEP, PIPELINE_STEPS

        sql = """
            SELECT p.id, p.service, p.step, p.step_date, c.name AS client_name
            FROM pipeline_items p
            LEFT JOIN clients c ON c.id = p.client_id AND c.deleted_at IS NULL
            WHERE p.deleted_at IS NULL AND p.step < ?
              AND (c.id IS NULL OR COALESCE(c.status, 'active') != 'inactive')
            ORDER BY p.step ASC, p.updated_at DESC
            LIMIT ?
        """
        rows = self._safe_fetch_all(sql, (PIPELINE_MAX_STEP, limit))
        for row in rows:
            step = int(row.get("step") or 0)
            if 1 <= step <= len(PIPELINE_STEPS):
                row["step_label"] = PIPELINE_STEPS[step - 1]
            else:
                row["step_label"] = f"Step {step}"
        return rows

    def get_overdue_documents(self) -> list[dict]:
        """Unpaid docs past payment_date — mirrors dashboard list_overdue_services."""
        from ._overdue import query_overdue_documents

        return query_overdue_documents(self._db, self._safe_fetch_all)

    def get_expiring_within(self, within_days: int) -> list[dict]:
        """Companies → Expiry style: 0..within_days left (effective dates)."""
        from ._expiring import query_expiring_within

        return query_expiring_within(self._db, within_days)

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
