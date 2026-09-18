from __future__ import annotations

from skyadmin_pro.db.sql_helpers import _escape_like


class TasksMixinMixin0:
    def list_tasks(
        self: CoreMixin,
        status: str | None = None,
        *,
        q: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        exclude_expired: bool = False,
    ) -> list[dict]:
        sql = """
            SELECT t.id, t.client_id, t.title, t.description, t.status, t.category,
                   t.due_date, t.completed_at, t.created_at, t.updated_at,
                   t.pipeline_item_id, t.pipeline_step, t.source_document_id,
                   t.parent_task_id,
                   c.name AS client_name
            FROM tasks t
            LEFT JOIN clients c ON c.id = t.client_id
        """
        where_clauses: list[str] = []
        params_list: list[object] = []
        if status:
            where_clauses.append("t.status = ?")
            params_list.append(status)
        if q and q.strip():
            escaped = f"%{_escape_like(q.strip())}%"
            where_clauses.append(
                "(t.title LIKE ? ESCAPE '\\' OR c.name LIKE ? ESCAPE '\\' OR t.category LIKE ? ESCAPE '\\')"
            )
            params_list.extend([escaped, escaped, escaped])
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += """
            ORDER BY CASE t.status WHEN 'pending' THEN 0 ELSE 1 END,
                     CASE WHEN t.due_date IS NULL OR t.due_date = '' THEN 1 ELSE 0 END,
                     t.due_date,
                     t.id DESC
        """
        params = tuple(params_list)
        if limit is not None and int(limit) > 0:
            return self._fetch_page(sql, params, limit=limit, offset=offset)
        return self._fetch_all(sql, params)

    def count_tasks(self, status: str | None = None, *, q: str | None = None) -> int:
        sql = """
            SELECT COUNT(*) AS n
            FROM tasks t
            LEFT JOIN clients c ON c.id = t.client_id
        """
        where_clauses: list[str] = []
        params_list: list[object] = []
        if status:
            where_clauses.append("t.status = ?")
            params_list.append(status)
        if q and q.strip():
            escaped = f"%{_escape_like(q.strip())}%"
            where_clauses.append(
                "(t.title LIKE ? ESCAPE '\\' OR c.name LIKE ? ESCAPE '\\' OR t.category LIKE ? ESCAPE '\\')"
            )
            params_list.extend([escaped, escaped, escaped])
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        row = self._fetch_one(sql, tuple(params_list))
        return int(row["n"]) if row else 0

    def get_task(self, task_id: int) -> dict | None:
        return self._fetch_one(
            """
            SELECT t.id, t.client_id, t.title, t.description, t.status, t.category,
                   t.due_date, t.completed_at, t.created_at, t.updated_at,
                   t.pipeline_item_id, t.pipeline_step, t.source_document_id,
                   c.name AS client_name
            FROM tasks t
            LEFT JOIN clients c ON c.id = t.client_id
            WHERE t.id = ?
            """,
            (task_id,),
        )
