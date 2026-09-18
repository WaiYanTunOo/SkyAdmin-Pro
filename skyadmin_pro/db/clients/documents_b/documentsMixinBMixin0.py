from __future__ import annotations


class DocumentsMixinBMixin0:
    def update_document(
        self,
        document_id: int,
        *,
        document_type: str,
        expiry_date: str | None = None,
        amount: str | None = None,
        payment_date: str | None = None,
        start_date: str | None = None,
        progress: str | None = None,
        paid: bool | None = None,
        file_name: str | None = None,
        file_path: str | None = None,
        clear: bool = False,
    ) -> None:
        if clear:
            # Plain assignment: empty/None values genuinely clear the field.
            with self.connection() as conn:
                conn.execute(
                    """
                    UPDATE documents
                    SET document_type = ?,
                        expiry_date = ?,
                        amount = ?,
                        payment_date = ?,
                        start_date = ?,
                        progress = ?,
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
            return
        self._DocumentsMixinB_update_document_p1(
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
        )

    def update_document_amount_and_date(
        self, document_id: int, document_type: str, amount: str | None, payment_date: str | None
    ) -> None:
        """Narrow update for the incentive view that sets type, amount, and date without wiping expiry or files."""
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE documents
                SET document_type = ?, amount = ?, payment_date = ?
                WHERE id = ?
                """,
                (document_type, amount, payment_date, document_id),
            )
