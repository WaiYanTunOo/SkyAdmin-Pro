"""Database Tax operations."""

from __future__ import annotations


class StatusMixinB:
    def month_close_summary(self, month_key: str, client_ids: list[int] | None = None) -> dict[str, int]:
        """Month-close counts for a calendar month_key (YYYY-MM).

        - ``closed`` / ``in_progress``: rows with those statuses (active clients).
        - ``open``: not closed and not in_progress (status ``open`` or no row yet).
        - ``incomplete``: not closed — ``open`` + ``in_progress`` (Money/dashboard headline).
        """
        if client_ids is None:
            with self.connection() as conn:
                total = conn.execute("SELECT COUNT(*) AS n FROM clients WHERE deleted_at IS NULL").fetchone()["n"]
                closed = conn.execute(
                    """
                    SELECT COUNT(*) AS n FROM client_months cm
                    INNER JOIN clients c ON c.id = cm.client_id
                    WHERE cm.month_key = ? AND cm.status = 'closed'
                      AND cm.deleted_at IS NULL AND c.deleted_at IS NULL
                    """,
                    (month_key,),
                ).fetchone()["n"]
                in_progress = conn.execute(
                    """
                    SELECT COUNT(*) AS n FROM client_months cm
                    INNER JOIN clients c ON c.id = cm.client_id
                    WHERE cm.month_key = ? AND cm.status = 'in_progress'
                      AND cm.deleted_at IS NULL AND c.deleted_at IS NULL
                    """,
                    (month_key,),
                ).fetchone()["n"]
        else:
            scope = sorted(set(int(cid) for cid in client_ids))
            total = len(scope)
            closed = in_progress = 0
            if scope:
                placeholders = ", ".join("?" for _ in scope)
                with self.connection() as conn:
                    rows = conn.execute(
                        f"""
                        SELECT cm.status, COUNT(*) AS n FROM client_months cm
                        INNER JOIN clients c ON c.id = cm.client_id
                        WHERE cm.month_key = ? AND cm.client_id IN ({placeholders})
                          AND cm.deleted_at IS NULL AND c.deleted_at IS NULL
                        GROUP BY cm.status
                        """,
                        (month_key, *scope),
                    ).fetchall()
                by_status = {row["status"]: row["n"] for row in rows}
                closed = int(by_status.get("closed", 0))
                in_progress = int(by_status.get("in_progress", 0))
        open_count = max(0, int(total) - int(closed) - int(in_progress))
        incomplete = max(0, int(total) - int(closed))  # open + in_progress only
        return {
            "clients": int(total),
            "closed": int(closed),
            "in_progress": int(in_progress),
            "open": open_count,
            "incomplete": incomplete,
        }
