"""Database Clients operations."""

from __future__ import annotations

from skyadmin_pro.db.soft_delete_cascade import soft_delete_clients_cascade


class BatchMixinA:
    def batch_delete_clients(self, client_ids: list[int], *, now: str | None = None) -> int:
        """Soft-delete clients + synced children. Returns count tombstoned."""

        if not client_ids:
            return 0

        stamp = now or self._now()

        with self.connection() as conn:
            count = soft_delete_clients_cascade(conn, client_ids, stamp)

        self._client_names_cache = None

        return count

    def batch_update_client_status(self, client_ids: list[int], status: str) -> int:
        """Update status for multiple clients. Returns count updated."""

        if not client_ids:
            return 0

        normalized = (status or "").strip().lower()

        if normalized not in {"active", "inactive"}:
            raise ValueError("Status must be active or inactive.")

        placeholders = ",".join("?" for _ in client_ids)

        with self.connection() as conn:
            cursor = conn.execute(
                f"UPDATE clients SET status = ?, updated_at = ? WHERE id IN ({placeholders}) AND deleted_at IS NULL",
                [normalized, self._now(), *client_ids],
            )

            count = cursor.rowcount

        self._client_names_cache = None

        return count

    def batch_assign_client_group(self, client_ids: list[int], group_id: int | None) -> int:
        """Assign (or clear) local group for multiple clients. Returns count updated.



        ``group_id`` is local-only and is never synced.

        """

        if not client_ids:
            return 0

        if group_id is not None:
            group = self._fetch_one("SELECT id FROM client_groups WHERE id = ?", (group_id,))

            if group is None:
                raise ValueError("Group not found.")

        placeholders = ",".join("?" for _ in client_ids)

        with self.connection() as conn:
            cursor = conn.execute(
                f"UPDATE clients SET group_id = ?, updated_at = ? WHERE id IN ({placeholders}) AND deleted_at IS NULL",
                [group_id, self._now(), *client_ids],
            )

            count = cursor.rowcount

        return count

    def batch_archive_clients(self, client_ids: list[int]) -> int:
        """Soft-delete clients by setting ``deleted_at``. Returns count archived."""

        if not client_ids:
            return 0

        now = self._now()

        placeholders = ",".join("?" for _ in client_ids)

        with self.connection() as conn:
            cursor = conn.execute(
                f"UPDATE clients SET deleted_at = ?, updated_at = ?"
                f" WHERE id IN ({placeholders}) AND deleted_at IS NULL",
                [now, now, *client_ids],
            )

            count = cursor.rowcount

        self._client_names_cache = None

        return count
