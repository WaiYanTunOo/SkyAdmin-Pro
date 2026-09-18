"""Database Clients operations."""

from __future__ import annotations

from skyadmin_pro.db.sql_helpers import (
    _in_clause,
)


class DocListMixin:
    def list_client_documents(self, client_id: int) -> list[dict]:
        clause, params = _in_clause("d.document_type", tuple(self.list_service_types()))
        return self._fetch_all(
            f"""
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.start_date, d.progress, d.paid, d.file_name, d.file_path,
                   d.created_at, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.client_id = ? AND NOT {clause}
            ORDER BY d.created_at DESC, d.id DESC
            """,
            (client_id, *params),
        )
