from __future__ import annotations

from skyadmin_pro.config import service_task_category
from skyadmin_pro.db.soft_delete import soft_delete_by_id


class TasksMixinMixin2:
    def set_task_status(self, task_id: int, status: str) -> None:
        if status not in {"pending", "completed"}:
            raise ValueError("Status must be pending or completed.")

        with self.connection() as conn:
            if status == "completed":
                parent_row = conn.execute(
                    """
                    SELECT p.status FROM tasks c
                    JOIN tasks p ON p.id = c.parent_task_id
                    WHERE c.id = ? AND c.deleted_at IS NULL
                    """,
                    (task_id,),
                ).fetchone()
                if parent_row and parent_row["status"] != "completed":
                    raise ValueError("Cannot complete task because its parent task is still pending.")

            now = self._now()
            completed_at = now if status == "completed" else None
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, completed_at = ?, updated_at = ?
                WHERE id = ? AND deleted_at IS NULL
                """,
                (status, completed_at, now, task_id),
            )

    def delete_task(self, task_id: int) -> None:
        with self.connection() as conn:
            # Soft-delete keeps a sync tombstone; detach renewals so the
            # audit trail is not tied to a tombstoned task row.
            conn.execute(
                "UPDATE service_renewals SET task_id = NULL WHERE task_id = ?",
                (task_id,),
            )
            soft_delete_by_id(conn, "tasks", task_id, self._now())

    def sync_service_progress_task(self, document_id: int) -> None:
        """Keep one "Continue: <service>" task in step with a service's progress.

        Marking a service Ongoing creates (once) a pending task linked to the
        service record; marking it Completed completes that task, so ongoing
        work shows up in Tasks and on the Dashboard until it is finished.
        """
        doc = self._fetch_one(
            "SELECT id, client_id, document_type, progress FROM documents" " WHERE id = ? AND deleted_at IS NULL",
            (document_id,),
        )
        if not doc:
            return
        progress = (doc.get("progress") or "").strip()
        if progress == "Ongoing":
            linked = self._fetch_one(
                "SELECT id FROM tasks WHERE source_document_id = ? AND deleted_at IS NULL",
                (document_id,),
            )
            if linked is None:
                self.add_task(
                    title=f"Continue: {doc['document_type']}",
                    client_id=doc.get("client_id"),
                    description=(
                        f"Service record: {doc['document_type']}. "
                        "Keep the client's ongoing work up to date and mark "
                        "the service Completed when finished."
                    ),
                    category=service_task_category(doc["document_type"]),
                    source_document_id=document_id,
                )
        elif progress == "Completed":
            linked = self._fetch_one(
                "SELECT id, status FROM tasks WHERE source_document_id = ?" " AND deleted_at IS NULL",
                (document_id,),
            )
            if linked is not None and linked["status"] == "pending":
                self.set_task_status(linked["id"], "completed")

    def list_completed_today(self) -> list[dict]:
        return self._fetch_all(
            """
            SELECT t.id, t.title, t.category, t.completed_at, c.name AS client_name
            FROM tasks t
            LEFT JOIN clients c ON c.id = t.client_id
            WHERE t.status = 'completed' AND t.deleted_at IS NULL
              -- lexical compare on 'YYYY-MM-DD HH:MM:SS' keeps idx usable
              AND t.completed_at >= date('now', 'localtime')
              AND t.completed_at <  date('now', 'localtime', '+1 day')
            ORDER BY t.completed_at DESC
            """
        )
