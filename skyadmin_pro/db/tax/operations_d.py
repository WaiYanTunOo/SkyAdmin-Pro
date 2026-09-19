"""Database Tax operations."""

from __future__ import annotations


class OperationsMixinD:
    def delete_vo_csh_renewal(self, client_id: int, renewal_type: str) -> None:
        """Soft-delete renewal item and pending task for VO/CSH when date is cleared."""

        template = "VO Renewal" if renewal_type == "vo" else "CSH Renewal"

        label = "VO" if renewal_type == "vo" else "CSH"

        client = self.get_client(client_id)

        client_name = (client or {}).get("name") or "client"

        task_title = f"Renew {label} for {client_name}"

        now = self._now()

        with self.connection() as conn:
            conn.execute(
                "UPDATE renewal_items SET deleted_at = ?, updated_at = ?"
                " WHERE client_id = ? AND template_name = ? AND deleted_at IS NULL",
                (now, now, client_id, template),
            )

            conn.execute(
                "UPDATE tasks SET deleted_at = ?, updated_at = ?"
                " WHERE client_id = ? AND title = ? AND status = 'pending'"
                " AND deleted_at IS NULL",
                (now, now, client_id, task_title),
            )
