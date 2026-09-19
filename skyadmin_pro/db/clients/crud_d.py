"""Database Clients operations."""

from __future__ import annotations

from skyadmin_pro.db.soft_delete_cascade import soft_delete_clients_cascade


class CrudMixinD:
    def delete_client(self, client_id: int) -> None:
        now = self._now()

        with self.connection() as conn:
            soft_delete_clients_cascade(conn, [client_id], now)

        self._client_names_cache = None
