from __future__ import annotations

from skyadmin_pro.config import PIPELINE_MAX_STEP


class PipelineMixinMixin0:
    def add_pipeline_item(self: CoreMixin, *, client_id: int, service: str, step: int = 1) -> int:
        cleaned = service.strip()
        if not cleaned:
            raise ValueError("Enter a service name.")
        step = max(1, min(int(step), PIPELINE_MAX_STEP))
        now = self._now()
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO pipeline_items (client_id, service, step, step_date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (client_id, cleaned, step, now[:10] if step else None, now, now),
            )
            item_id = int(cursor.lastrowid)
        self.sync_pipeline_tasks(item_id)
        return item_id

    def list_pipeline_items(self, *, limit: int | None = None, offset: int = 0) -> list[dict]:
        base = """
            SELECT p.id, p.client_id, p.service, p.step, p.step_date, p.notes,
                   p.created_at, p.updated_at, c.name AS client_name
            FROM pipeline_items p
            LEFT JOIN clients c ON c.id = p.client_id
            ORDER BY p.step ASC, p.updated_at DESC
            """
        if limit is not None and int(limit) > 0:
            return self._fetch_page(base, (), limit=limit, offset=offset)
        return self._fetch_all(base)

    def get_pipeline_item(self, item_id: int) -> dict | None:
        return self._fetch_one("SELECT * FROM pipeline_items WHERE id = ?", (item_id,))

    def set_pipeline_step(self, item_id: int, step: int) -> None:
        step = max(1, min(int(step), PIPELINE_MAX_STEP))
        now = self._now()
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE pipeline_items
                SET step = ?, step_date = ?, updated_at = ?
                WHERE id = ?
                """,
                (step, now[:10], now, item_id),
            )
        self.sync_pipeline_tasks(item_id)

    def advance_pipeline(self, item_id: int) -> None:
        item = self.get_pipeline_item(item_id)
        if item is None:
            return
        self.set_pipeline_step(item_id, int(item["step"]) + 1)

    def update_pipeline_item(self, item_id: int, *, service: str | None = None, notes: str | None = None) -> None:
        item = self.get_pipeline_item(item_id)
        if item is None:
            return
        service = (service or item["service"]).strip()
        if not service:
            raise ValueError("Enter a service name.")
        notes = item["notes"] if notes is None else notes
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE pipeline_items SET service = ?, notes = ?, updated_at = ?
                WHERE id = ?
                """,
                (service, notes, self._now(), item_id),
            )

    def delete_pipeline_item(self, item_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM tasks WHERE pipeline_item_id = ?", (item_id,))
            conn.execute("DELETE FROM pipeline_items WHERE id = ?", (item_id,))
