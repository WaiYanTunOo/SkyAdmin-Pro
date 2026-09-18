"""Database Clients operations."""

from __future__ import annotations


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

    # -- Client groups --------------------------------------------------
