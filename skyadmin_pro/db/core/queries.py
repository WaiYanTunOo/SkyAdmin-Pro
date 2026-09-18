"""Database Core operations."""

from __future__ import annotations


class QueryMixin:
    def _fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.read_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def _fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        with self.read_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return dict(row) if row is not None else None

    @staticmethod
    def _apply_pagination(sql: str, limit: int | None, offset: int | None) -> tuple[str, tuple]:
        """Append LIMIT/OFFSET safely. limit<=0 means no limit."""
        extra: list[str] = []
        extra_params: list = []
        if limit is not None and int(limit) > 0:
            extra.append("LIMIT ?")
            extra_params.append(int(limit))
            if offset is not None and int(offset) > 0:
                extra.append("OFFSET ?")
                extra_params.append(int(offset))
        elif offset is not None and int(offset) > 0:
            # SQLite requires LIMIT with OFFSET; -1 = no limit.
            extra.append("LIMIT -1 OFFSET ?")
            extra_params.append(int(offset))
        if not extra:
            return sql, ()
        return f"{sql} {' '.join(extra)}", tuple(extra_params)

    def _fetch_page(self, base_sql: str, params: tuple = (), *, limit: int | None = 250, offset: int = 0) -> list[dict]:
        """Fetch one page with LIMIT/OFFSET. limit=None/<=0 disables paging."""
        paged_sql, page_params = self._apply_pagination(base_sql, limit, offset)
        return self._fetch_all(paged_sql, tuple(params) + tuple(page_params))
