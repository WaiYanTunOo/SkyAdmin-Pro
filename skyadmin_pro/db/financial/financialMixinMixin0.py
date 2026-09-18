from __future__ import annotations


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
    ) -> int:
        """Insert a financial document record. Returns the new row id."""
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO financial_documents
                    (client_id, category, subcategory, file_name, file_path,
                     stored_path, amount, doc_date, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                WHERE client_id = ? AND category = ?
                ORDER BY doc_date DESC, created_at DESC
                """,
                (client_id, category),
            )
        return self._fetch_all(
            """
            SELECT id, client_id, category, subcategory, file_name, file_path,
                   stored_path, amount, doc_date, description, created_at
            FROM financial_documents
            WHERE client_id = ?
            ORDER BY doc_date DESC, created_at DESC
            """,
            (client_id,),
        )

    def get_financial_document(self, doc_id: int) -> dict | None:
        return self._fetch_one(
            """
            SELECT id, client_id, category, subcategory, file_name, file_path,
                   stored_path, amount, doc_date, description, created_at
            FROM financial_documents WHERE id = ?
            """,
            (doc_id,),
        )

    def delete_financial_document(self, doc_id: int) -> dict | None:
        """Delete a financial document. Returns the deleted record (for file cleanup)."""
        doc = self.get_financial_document(doc_id)
        if doc:
            with self.connection() as conn:
                conn.execute("DELETE FROM financial_documents WHERE id = ?", (doc_id,))
        return doc
