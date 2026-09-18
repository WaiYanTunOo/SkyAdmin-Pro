"""Database Clients operations."""

from __future__ import annotations

from skyadmin_pro.db.cipher import INTEGRITY_ERRORS


class GroupsMixin:
    def list_client_groups(self) -> list[dict]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, name, color, global_id
                FROM client_groups
                WHERE deleted_at IS NULL
                ORDER BY name COLLATE NOCASE
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def add_client_group(self, name: str, color: str | None = None) -> int:
        import uuid

        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("Group name is required.")
        with self.connection() as conn:
            try:
                cur = conn.execute(
                    """
                    INSERT INTO client_groups (name, color, global_id, updated_at)
                    VALUES (?, ?, ?, datetime('now', 'localtime'))
                    """,
                    (cleaned, color, uuid.uuid4().hex),
                )
            except INTEGRITY_ERRORS:
                raise ValueError("A group with that name already exists.") from None
        return int(cur.lastrowid)

    def update_client_group(self, group_id: int, name: str, color: str | None = None) -> int:
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("Group name is required.")
        with self.connection() as conn:
            try:
                cur = conn.execute(
                    """
                    UPDATE client_groups
                    SET name = ?, color = ?, updated_at = datetime('now', 'localtime')
                    WHERE id = ? AND deleted_at IS NULL
                    """,
                    (cleaned, color, group_id),
                )
            except INTEGRITY_ERRORS:
                raise ValueError("A group with that name already exists.") from None
        return cur.rowcount

    def delete_client_group(self, group_id: int) -> int:
        """Soft-delete a group (clients in it become ungrouped). Synced via deleted_at."""
        with self.connection() as conn:
            conn.execute("UPDATE clients SET group_id = NULL WHERE group_id = ?", (group_id,))
            cur = conn.execute(
                """
                UPDATE client_groups
                SET deleted_at = datetime('now', 'localtime'),
                    updated_at = datetime('now', 'localtime')
                WHERE id = ? AND deleted_at IS NULL
                """,
                (group_id,),
            )
        return cur.rowcount
