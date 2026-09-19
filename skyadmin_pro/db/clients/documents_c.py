"""Database Clients operations."""

from __future__ import annotations

from skyadmin_pro.db.sql_helpers import (
    _in_clause,
)


class DocumentsMixinC:
    def set_document_paid(self, document_id: int, paid: bool = True) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE documents SET paid = ? WHERE id = ?",
                (1 if paid else 0, document_id),
            )

    def get_document(self, document_id: int) -> dict | None:
        return self._fetch_one(
            """
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.start_date, d.progress, d.file_name, d.file_path,
                   d.completed_at, d.created_at, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.id = ? AND d.deleted_at IS NULL
            """,
            (document_id,),
        )

    def list_client_services(self, client_id: int) -> list[dict]:
        clause, params = _in_clause("d.document_type", tuple(self.list_service_types()))
        return self._fetch_all(
            f"""
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.start_date, d.progress, d.paid, d.file_name, d.file_path,
                   d.completed_at, d.created_at, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.client_id = ? AND d.deleted_at IS NULL AND {clause}
            ORDER BY d.expiry_date IS NULL, d.expiry_date, d.id DESC
            """,
            (client_id, *params),
        )
