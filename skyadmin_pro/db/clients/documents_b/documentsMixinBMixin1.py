from __future__ import annotations


class DocumentsMixinBMixin1:
    def _DocumentsMixinB_update_document_p1(
        self,
        amount,
        document_id,
        document_type,
        expiry_date,
        file_name,
        file_path,
        paid,
        payment_date,
        progress,
        start_date,
    ):
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE documents
                SET document_type = ?,
                    expiry_date = COALESCE(?, expiry_date),
                    amount = COALESCE(?, amount),
                    payment_date = COALESCE(?, payment_date),
                    start_date = COALESCE(?, start_date),
                    progress = COALESCE(?, progress),
                    paid = CASE WHEN ? IS NULL THEN paid ELSE ? END,
                    file_name = COALESCE(?, file_name),
                    file_path = COALESCE(?, file_path),
                    completed_at = CASE
                        WHEN ? IS NOT NULL AND ? = 'Completed'
                            THEN datetime('now', 'localtime')
                        WHEN ? IS NOT NULL AND ? != 'Completed'
                            THEN NULL
                        ELSE completed_at
                    END
                WHERE id = ?
                """,
                (
                    document_type,
                    expiry_date,
                    amount,
                    payment_date,
                    start_date,
                    progress,
                    None if paid is None else (1 if paid else 0),
                    None if paid is None else (1 if paid else 0),
                    file_name,
                    file_path,
                    progress,
                    progress,
                    progress,
                    progress,
                    document_id,
                ),
            )
        self.sync_service_progress_task(document_id)
