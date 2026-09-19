"""Database Clients operations."""

from __future__ import annotations

from skyadmin_pro.db.soft_delete_cascade import restore_clients_cascade


class BatchMixinB:
    def batch_restore_clients(self, client_ids: list[int]) -> int:
        """Clear ``deleted_at`` for archived clients. Returns count restored."""

        if not client_ids:
            return 0

        placeholders = ",".join("?" for _ in client_ids)

        with self.connection() as conn:
            cursor = conn.execute(
                f"UPDATE clients SET deleted_at = NULL, updated_at = ?"
                f" WHERE id IN ({placeholders}) AND deleted_at IS NOT NULL",
                [self._now(), *client_ids],
            )

            count = cursor.rowcount

        self._client_names_cache = None

        return count

    def batch_restore_deleted_clients(self, client_ids: list[int], stamp: str) -> int:
        """Undo cascade soft-delete stamped with ``stamp``."""

        if not client_ids or not stamp:
            return 0

        now = self._now()

        with self.connection() as conn:
            count = restore_clients_cascade(conn, client_ids, stamp, now)

        self._client_names_cache = None

        return count
