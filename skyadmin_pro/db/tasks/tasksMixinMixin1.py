from __future__ import annotations


class TasksMixinMixin1:
    def add_task(
        self,
        *,
        title: str,
        client_id: int | None = None,
        description: str = "",
        category: str = "General",
        due_date: str | None = None,
        status: str = "pending",
        pipeline_item_id: int | None = None,
        pipeline_step: int | None = None,
        source_document_id: int | None = None,
        parent_task_id: int | None = None,
    ) -> int:
        cleaned = title.strip()
        if not cleaned:
            raise ValueError("Task title is required.")
        if status not in ("pending", "completed"):
            raise ValueError(f"Invalid task status: {status!r}")
        now = self._now()
        completed_at = now if status == "completed" else None
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks (
                    client_id, title, description, status, category,
                    due_date, completed_at, pipeline_item_id, pipeline_step,
                    source_document_id, parent_task_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client_id,
                    cleaned,
                    description.strip() or None,
                    status,
                    category,
                    due_date,
                    completed_at,
                    pipeline_item_id,
                    pipeline_step,
                    source_document_id,
                    parent_task_id,
                    now,
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def update_task(
        self,
        task_id: int,
        *,
        title: str,
        client_id: int | None = None,
        description: str = "",
        category: str = "General",
        due_date: str | None = None,
        parent_task_id: int | None = None,
    ) -> None:
        cleaned = title.strip()
        if not cleaned:
            raise ValueError("Task title is required.")
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET client_id = ?, title = ?, description = ?, category = ?,
                    due_date = ?, parent_task_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    client_id,
                    cleaned,
                    description.strip() or None,
                    category,
                    due_date,
                    parent_task_id,
                    self._now(),
                    task_id,
                ),
            )
