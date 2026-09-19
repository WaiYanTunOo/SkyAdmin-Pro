from __future__ import annotations

from skyadmin_pro.db.sql_helpers import _escape_like


class FinancialMixinMixin1:
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
                WHERE fd.deleted_at IS NULL AND fd.category = ?
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
            WHERE fd.deleted_at IS NULL
              AND (fd.file_name LIKE ? ESCAPE '\\' OR fd.description LIKE ? ESCAPE '\\'
               OR fd.amount LIKE ? ESCAPE '\\')
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
            WHERE client_id = ? AND deleted_at IS NULL
            GROUP BY category
            ORDER BY category
            """,
            (client_id,),
        )
        return {row["category"]: int(row["n"]) for row in rows}

    def all_financial_documents(self, category: str | None = None, client_id: int | None = None) -> list[dict]:
        """List all financial documents across clients with optional filters."""
        conditions = ["fd.deleted_at IS NULL"]
        params: list = []
        if category:
            conditions.append("fd.category = ?")
            params.append(category)
        if client_id:
            conditions.append("fd.client_id = ?")
            params.append(client_id)
        where = " WHERE " + " AND ".join(conditions)
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
