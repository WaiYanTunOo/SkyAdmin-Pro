"""Database Tax operations."""

from __future__ import annotations


class StatusMixinB:
    def month_close_summary(self, month_key: str, client_ids: list[int] | None = None) -> dict[str, int]:
        if client_ids is None:
            with self.connection() as conn:
                total = conn.execute("SELECT COUNT(*) AS n FROM clients").fetchone()["n"]
                closed = conn.execute(
                    """
                    SELECT COUNT(*) AS n FROM client_months
                    WHERE month_key = ? AND status = 'closed'
                    """,
                    (month_key,),
                ).fetchone()["n"]
                in_progress = conn.execute(
                    """
                    SELECT COUNT(*) AS n FROM client_months
                    WHERE month_key = ? AND status = 'in_progress'
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
                        SELECT status, COUNT(*) AS n FROM client_months
                        WHERE month_key = ? AND client_id IN ({placeholders})
                        GROUP BY status
                        """,
                        (month_key, *scope),
                    ).fetchall()
                by_status = {row["status"]: row["n"] for row in rows}
                closed = int(by_status.get("closed", 0))
                in_progress = int(by_status.get("in_progress", 0))
        return {
            "clients": int(total),
            "closed": int(closed),
            "in_progress": int(in_progress),
            "open": max(0, int(total) - int(closed) - int(in_progress)),
        }
