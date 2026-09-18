"""Database Tax operations."""

from __future__ import annotations

from skyadmin_pro.config import (
    MONTHLY_TAX_TYPES,
)


class StatusMixinA:
    def set_client_month_status(self, client_id: int, month_key: str, status: str, note: str = "") -> None:
        if status not in {"open", "in_progress", "closed"}:
            raise ValueError("Status must be open, in_progress or closed.")
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO client_months (client_id, month_key, status, note, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(client_id, month_key) DO UPDATE SET
                    status = excluded.status,
                    note = excluded.note,
                    updated_at = excluded.updated_at
                """,
                (client_id, month_key, status, (note or "").strip() or None, self._now()),
            )

    def list_client_month_status(self, month_key: str) -> dict[int, dict]:
        rows = self._fetch_all(
            """
            SELECT client_id, status, note, updated_at
            FROM client_months
            WHERE month_key = ?
            """,
            (month_key,),
        )
        return {int(row["client_id"]): row for row in rows}

    def list_monthly_tax_clients(self) -> list[dict]:
        """Clients with an active monthly tax / month-close service."""
        return self._fetch_all(
            f"""
            SELECT DISTINCT c.id, c.name
            FROM clients c
            JOIN documents d ON d.client_id = c.id
            WHERE d.document_type IN ({", ".join("?" for _ in MONTHLY_TAX_TYPES)})
            ORDER BY c.name COLLATE NOCASE
            """,
            tuple(MONTHLY_TAX_TYPES),
        )
