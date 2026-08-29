"""Database Financial operations."""

from __future__ import annotations

from skyadmin_pro.db.sql_helpers import (
    _escape_like,
)


class FinancialMixin:
    def add_financial_document(
        self,
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
        return cursor.lastrowid  # type: ignore[return-value]

    def list_financial_documents(self, client_id: int, category: str | None = None) -> list[dict]:
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

    def search_financial_documents(self, query: str, category: str | None = None) -> list[dict]:
        """Cross-client search by file name, description, or amount."""
        q = f"%{_escape_like(query)}%"
        if category:
            return self._fetch_all(
                """
                SELECT fd.id, fd.client_id, c.name AS client_name,
                       fd.category, fd.subcategory, fd.file_name,
                       fd.amount, fd.doc_date, fd.description
                FROM financial_documents fd
                LEFT JOIN clients c ON fd.client_id = c.id
                WHERE fd.category = ?
                  AND (fd.file_name LIKE ? ESCAPE '\\' OR fd.description LIKE ? ESCAPE '\\'
                       OR fd.amount LIKE ? ESCAPE '\\')
                ORDER BY fd.doc_date DESC, fd.created_at DESC
                """,
                (category, q, q, q),
            )
        return self._fetch_all(
            """
            SELECT fd.id, fd.client_id, c.name AS client_name,
                   fd.category, fd.subcategory, fd.file_name,
                   fd.amount, fd.doc_date, fd.description
            FROM financial_documents fd
            LEFT JOIN clients c ON fd.client_id = c.id
            WHERE fd.file_name LIKE ? ESCAPE '\\' OR fd.description LIKE ? ESCAPE '\\'
               OR fd.amount LIKE ? ESCAPE '\\'
            ORDER BY fd.doc_date DESC, fd.created_at DESC
            """,
            (q, q, q),
        )

    def financial_doc_summary(self, client_id: int) -> dict[str, int]:
        """Return counts of financial documents by category for a client."""
        rows = self._fetch_all(
            """
            SELECT category, COUNT(*) AS n
            FROM financial_documents
            WHERE client_id = ?
            GROUP BY category
            ORDER BY category
            """,
            (client_id,),
        )
        return {row["category"]: int(row["n"]) for row in rows}

    def all_financial_documents(self, category: str | None = None, client_id: int | None = None) -> list[dict]:
        """List all financial documents across clients with optional filters."""
        conditions = []
        params: list = []
        if category:
            conditions.append("fd.category = ?")
            params.append(category)
        if client_id:
            conditions.append("fd.client_id = ?")
            params.append(client_id)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        return self._fetch_all(
            f"""
            SELECT fd.id, fd.client_id, c.name AS client_name,
                   fd.category, fd.subcategory, fd.file_name,
                   fd.amount, fd.doc_date, fd.description, fd.stored_path
            FROM financial_documents fd
            LEFT JOIN clients c ON fd.client_id = c.id
            {where}
            ORDER BY fd.doc_date DESC, fd.created_at DESC
            """,
            tuple(params),
        )

    # ------------------------------------------------------------------ #
    # Office contacts, password vault, notebook
    # ------------------------------------------------------------------ #
