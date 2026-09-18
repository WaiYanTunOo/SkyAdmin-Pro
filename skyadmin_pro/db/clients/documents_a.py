"""Database Clients operations."""

from __future__ import annotations


class DocumentsMixinA:
    def record_document(
        self,
        *,
        client_id: int | None,
        document_type: str,
        file_name: str,
        file_path: str,
        expiry_date: str | None = None,
        amount: str | None = None,
        payment_date: str | None = None,
        start_date: str | None = None,
        progress: str | None = None,
        paid: bool = False,
    ) -> int:
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO documents (
                    client_id, document_type, expiry_date, amount,
                    payment_date, start_date, progress, paid, file_name, file_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client_id,
                    document_type,
                    expiry_date,
                    amount,
                    payment_date,
                    start_date,
                    progress,
                    1 if paid else 0,
                    file_name,
                    file_path,
                ),
            )
            new_id = int(cursor.lastrowid)
        self.sync_service_progress_task(new_id)
        return new_id
