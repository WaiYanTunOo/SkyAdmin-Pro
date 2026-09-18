"""Database Tax operations."""

from __future__ import annotations


class FilingMixinA:
    def log_tax_change(self, client_id: int, field: str, old_value: str | None, new_value: str | None) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO tax_cycle_log (client_id, field, old_value, new_value, changed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (client_id, field, old_value, new_value, self._now()),
            )

    def get_client_tax_summary(self, client_id: int) -> dict[str, str]:
        client = self.get_client(client_id)
        if client is None:
            return {}
        return {
            "fs_status": client.get("fs_status") or "Not Applicable",
            "pnd53_status": client.get("pnd53_status") or "Not Applicable",
            "pp30_status": client.get("pp30_status") or "Not Applicable",
            "pnd51_status": client.get("pnd51_status") or "Not Applicable",
            "pnd50_status": client.get("pnd50_status") or "Not Applicable",
            "audit_status": client.get("audit_status") or "Not Applicable",
        }

    def list_clients_by_filing_status(self, field: str, status: str) -> list[dict]:
        if field not in {
            "fs_status",
            "pnd53_status",
            "pp30_status",
            "pnd51_status",
            "pnd50_status",
            "audit_status",
        }:
            return []
        return self._fetch_all(
            f"SELECT id, name FROM clients WHERE {field} = ? ORDER BY name COLLATE NOCASE",
            (status,),
        )

    def get_filing_change_history(self, client_id: int, limit: int = 20) -> list[dict]:
        """Return recent filing-status changes for a client, newest first."""
        return self._fetch_all(
            """
            SELECT id, field, old_value, new_value, changed_at
            FROM tax_cycle_log
            WHERE client_id = ?
            ORDER BY changed_at DESC, id DESC
            LIMIT ?
            """,
            (client_id, limit),
        )

    def get_filing_last_changed(self, client_id: int) -> str | None:
        """Return the most recent filing change timestamp for a client."""
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT changed_at FROM tax_cycle_log
                WHERE client_id = ?
                ORDER BY changed_at DESC, id DESC
                LIMIT 1
                """,
                (client_id,),
            ).fetchone()
        return row["changed_at"] if row else None
