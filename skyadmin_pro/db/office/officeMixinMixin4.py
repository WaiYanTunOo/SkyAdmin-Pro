from __future__ import annotations

from datetime import date

from skyadmin_pro.db.sql_helpers import _escape_like


class OfficeMixinMixin4:
    def list_notebook_entries(
        self,
        *,
        query: str = "",
        entry_type: str | None = None,
        client_id: int | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict]:
        sql = """
            SELECT n.*, c.name AS client_name
            FROM notebook_entries n
            LEFT JOIN clients c ON c.id = n.client_id
        """
        conditions: list[str] = []
        params: list = []
        q = (query or "").strip()
        if q:
            like = f"%{_escape_like(q)}%"
            conditions.append(
                "(n.title LIKE ? ESCAPE '\\' OR n.body LIKE ? ESCAPE '\\' OR n.author LIKE ? ESCAPE '\\')"
            )
            params.extend([like, like, like])
        if entry_type:
            conditions.append("n.entry_type = ?")
            params.append(entry_type)
        if client_id:
            conditions.append("n.client_id = ?")
            params.append(client_id)
        if from_date:
            conditions.append("n.entry_date >= ?")
            params.append(from_date)
        if to_date:
            conditions.append("n.entry_date <= ?")
            params.append(to_date)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY n.is_pinned DESC, n.entry_date DESC, n.id DESC"
        return self._fetch_all(sql, tuple(params))

    def get_notebook_entry(self, entry_id: int) -> dict | None:
        return self._fetch_one(
            """
            SELECT n.*, c.name AS client_name
            FROM notebook_entries n
            LEFT JOIN clients c ON c.id = n.client_id
            WHERE n.id = ?
            """,
            (entry_id,),
        )

    def add_notebook_entry(self, **fields: object) -> int:
        title = str(fields.get("title") or "").strip()
        if not title:
            raise ValueError("Notebook title is required.")
        entry_date = str(fields.get("entry_date") or date.today().isoformat())[:10]
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO notebook_entries
                    (entry_type, title, body, entry_date, client_id, author,
                     follow_up_date, is_pinned, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fields.get("entry_type") or "general",
                    title,
                    fields.get("body"),
                    entry_date,
                    fields.get("client_id"),
                    fields.get("author"),
                    fields.get("follow_up_date"),
                    1 if fields.get("is_pinned") else 0,
                    self._now(),
                ),
            )
            return int(cursor.lastrowid)
