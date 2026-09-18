"""Database Tax operations."""

from __future__ import annotations


class OperationsMixinD:
    def delete_vo_csh_renewal(self, client_id: int, renewal_type: str) -> None:
        """Remove renewal item and pending task for VO/CSH when date is cleared."""
        template = "VO Renewal" if renewal_type == "vo" else "CSH Renewal"
        label = "VO" if renewal_type == "vo" else "CSH"
        client = self.get_client(client_id)
        client_name = (client or {}).get("name") or "client"
        task_title = f"Renew {label} for {client_name}"
        with self.connection() as conn:
            conn.execute(
                "DELETE FROM renewal_items WHERE client_id = ? AND template_name = ?",
                (client_id, template),
            )
            conn.execute(
                "DELETE FROM tasks WHERE client_id = ? AND title = ? AND status = 'pending'",
                (client_id, task_title),
            )
