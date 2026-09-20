"""Database Tax operations."""

from __future__ import annotations

from datetime import date, timedelta


class OperationsMixinC:
    def create_vo_csh_renewal(self, client_id: int, renewal_type: str, renewal_date: str) -> int | None:
        """Auto-create a renewal item + task for VO or CSH renewal.

        *renewal_type* is ``"vo"`` or ``"csh"``.
        If a renewal item for this client+template already exists, its due date
        is updated instead of duplicating.  Returns the renewal item id, or
        *None* when *renewal_date* is empty.
        """
        if not renewal_date or not renewal_date.strip():
            return None
        template = "VO Renewal" if renewal_type == "vo" else "CSH Renewal"
        label = "VO" if renewal_type == "vo" else "CSH"
        client = self.get_client(client_id)
        client_name = (client or {}).get("name") or "client"
        # Due date = renewal_date minus 30 days. Strict parse: a garbage date
        # must fail loudly, never silently poison due-date sorting/alerts.
        try:
            due = (date.fromisoformat(renewal_date.strip()) - timedelta(days=30)).isoformat()
        except ValueError as exc:
            raise ValueError(f"Invalid renewal date: {renewal_date!r}") from exc
        # Upsert renewal item + create/update the reminder task in ONE
        # transaction so a crash can't leave an item without its task.
        task_title = f"Renew {label} for {client_name}"
        with self.connection() as conn:
            now = self._now()
            existing = conn.execute(
                "SELECT id FROM renewal_items WHERE client_id = ? AND template_name = ? LIMIT 1",
                (client_id, template),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE renewal_items SET due_days = 0, done = 0, done_at = NULL,"
                    " deleted_at = NULL, updated_at = ? WHERE id = ?",
                    (now, existing["id"]),
                )
                renewal_item_id = existing["id"]
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO renewal_items (client_id, template_name, item, due_days)
                    VALUES (?, ?, ?, 0)
                    """,
                    (client_id, template, f"{label} renewal for {client_name}"),
                )
                renewal_item_id = cursor.lastrowid
            existing_task = conn.execute(
                "SELECT id FROM tasks WHERE client_id = ? AND title = ?"
                " AND status = 'pending' AND deleted_at IS NULL LIMIT 1",
                (client_id, task_title),
            ).fetchone()
            if existing_task:
                conn.execute(
                    "UPDATE tasks SET due_date = ?, updated_at = ? WHERE id = ?",
                    (due, now, existing_task["id"]),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO tasks (client_id, title, description, status, category, due_date, created_at, updated_at)
                    VALUES (?, ?, ?, 'pending', 'General', ?, ?, ?)
                    """,
                    (client_id, task_title, f"Auto-created: {label} renewal due {due}", due, now, now),
                )
        return renewal_item_id
