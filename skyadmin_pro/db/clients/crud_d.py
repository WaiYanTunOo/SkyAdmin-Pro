"""Database Clients operations."""

from __future__ import annotations


class CrudMixinD:
    def delete_client(self, client_id: int) -> None:
        with self.connection() as conn:
            conn.execute(
                "DELETE FROM tasks WHERE pipeline_item_id IN (SELECT id FROM pipeline_items WHERE client_id = ?)",
                (client_id,),
            )
            conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        self._client_names_cache = None
