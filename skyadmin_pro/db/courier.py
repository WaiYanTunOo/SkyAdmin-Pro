"""Database Courier operations."""

from __future__ import annotations


class CourierMixin:
    def add_courier_log(
        self,
        *,
        tracking_number: str,
        driver_name: str,
        date_sent: str,
        client_id: int | None = None,
        task_id: int | None = None,
        destination: str | None = None,
        notes: str | None = None,
    ) -> int:
        tracking = tracking_number.strip()
        if not tracking:
            raise ValueError("Tracking number is required.")
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO courier_logs (
                    client_id, task_id, tracking_number, driver_name,
                    date_sent, destination, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client_id,
                    task_id,
                    tracking,
                    driver_name.strip() or None,
                    date_sent,
                    (destination or "").strip() or None,
                    (notes or "").strip() or None,
                ),
            )
            return int(cursor.lastrowid)

    def list_courier_logs(self, *, limit: int | None = None, offset: int = 0) -> list[dict]:
        base = """
            SELECT cl.id, cl.client_id, cl.task_id, cl.tracking_number, cl.driver_name,
                   cl.date_sent, cl.destination, cl.notes, cl.created_at,
                   c.name AS client_name, t.title AS task_title
            FROM courier_logs cl
            LEFT JOIN clients c ON c.id = cl.client_id
            LEFT JOIN tasks t ON t.id = cl.task_id
            ORDER BY cl.date_sent DESC, cl.id DESC
            """
        if limit is not None and int(limit) > 0:
            return self._fetch_page(base, (), limit=limit, offset=offset)
        return self._fetch_all(base)

    def delete_courier_log(self, log_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM courier_logs WHERE id = ?", (log_id,))

    # ------------------------------------------------------------------ #
    # 9-step client-to-supplier pipeline
    # ------------------------------------------------------------------ #
