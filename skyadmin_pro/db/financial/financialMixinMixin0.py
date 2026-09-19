from __future__ import annotations

from skyadmin_pro.db.soft_delete import soft_delete_by_id


class FinancialMixinMixin0:
    def add_financial_document(
        self: CoreMixin,
        *,
        client_id: int,
        category: str,
        subcategory: str = "",
        file_name: str,
        file_path: str,
        stored_path: str = "",
        amount: str = "",
        doc_date: str = "",
        description: str = "",
        drive_file_id: str = "",
    ) -> int:
        """Insert a financial document record. Returns the new row id."""
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO financial_documents
                    (client_id, category, subcategory, file_name, file_path,
                     stored_path, amount, doc_date, description, drive_file_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client_id,
                    category,
                    subcategory,
                    file_name,
                    file_path,
                    stored_path,
                    amount,
                    doc_date,
                    description,
                    drive_file_id,
                ),
            )
            return int(cursor.lastrowid)

    def list_financial_documents(self: CoreMixin, client_id: int, category: str | None = None) -> list[dict]:
        """List financial documents for a client, optionally filtered by category."""
        if category:
            return self._fetch_all(
                """
                SELECT id, client_id, category, subcategory, file_name, file_path,
                       stored_path, amount, doc_date, description, created_at
                FROM financial_documents
                WHERE client_id = ? AND category = ? AND deleted_at IS NULL
                ORDER BY doc_date DESC, created_at DESC
                """,
                (client_id, category),
            )
        return self._fetch_all(
            """
            SELECT id, client_id, category, subcategory, file_name, file_path,
                   stored_path, amount, doc_date, description, created_at
            FROM financial_documents
            WHERE client_id = ? AND deleted_at IS NULL
            ORDER BY doc_date DESC, created_at DESC
            """,
            (client_id,),
        )

    def get_financial_document(self, doc_id: int) -> dict | None:
        return self._fetch_one(
            """
            SELECT id, client_id, category, subcategory, file_name, file_path,
                   stored_path, amount, doc_date, description, created_at
            FROM financial_documents WHERE id = ? AND deleted_at IS NULL
            """,
            (doc_id,),
        )

    def delete_financial_document(self, doc_id: int) -> dict | None:
        """Soft-delete a financial document. Returns the record (for file cleanup)."""
        doc = self.get_financial_document(doc_id)
        if doc:
            with self.connection() as conn:
                soft_delete_by_id(conn, "financial_documents", doc_id, self._now())
        return doc
