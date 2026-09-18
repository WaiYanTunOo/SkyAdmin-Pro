from __future__ import annotations


class TasksMixinMixin5:
    def record_service_renewal(
        self,
        service_id: int,
        new_expiry: str,
        note: str = "",
        needs_documents: bool = True,
    ) -> int:
        """Extend a service: update its expiry, keep a history row, and create
        a linked pending task (so the renewal shows up on the dashboard).

        ``needs_documents`` marks whether this renewal requires the document
        checklist (e.g. Non-B / Passport renewals do; Virtual Office / CSH
        extensions usually do not). It can be toggled later.
        """
        category, description, doc_type, needs_documents, new_expiry, now, service, title = (
            self._TasksMixin_record_service_renewal_p1(service_id, new_expiry, needs_documents)
        )
        with self.connection() as conn:
            conn.execute(
                "UPDATE documents SET expiry_date = ? WHERE id = ?",
                (new_expiry, service_id),
            )
            task_cursor = conn.execute(
                """
                INSERT INTO tasks (
                    client_id, title, description, status, category,
                    due_date, completed_at, created_at, updated_at
                ) VALUES (?, ?, ?, 'pending', ?, ?, NULL, ?, ?)
                """,
                (
                    service.get("client_id"),
                    title,
                    description,
                    category,
                    new_expiry,
                    now,
                    now,
                ),
            )
            task_id = int(task_cursor.lastrowid)
            cursor = conn.execute(
                """
                INSERT INTO service_renewals
                    (service_id, client_id, document_type, previous_expiry,
                     new_expiry, note, needs_documents, task_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    service_id,
                    service.get("client_id"),
                    doc_type,
                    service.get("expiry_date"),
                    new_expiry,
                    (note or "").strip() or None,
                    1 if needs_documents else 0,
                    task_id,
                    now,
                ),
            )
        return int(cursor.lastrowid)

    def set_renewal_needs_documents(self, renewal_id: int, needs_documents: bool) -> None:
        """Edit whether a renewal requires documents (updates its task too)."""
        needs_documents = bool(needs_documents)
        with self.connection() as conn:
            row = conn.execute("SELECT task_id FROM service_renewals WHERE id = ?", (renewal_id,)).fetchone()
            if row is None:
                return
            conn.execute(
                "UPDATE service_renewals SET needs_documents = ? WHERE id = ?",
                (1 if needs_documents else 0, renewal_id),
            )
            if row["task_id"] is not None:
                conn.execute(
                    """
                    UPDATE tasks
                    SET description = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        (
                            "Documents required for this renewal."
                            if needs_documents
                            else "No documents required for this renewal."
                        ),
                        self._now(),
                        row["task_id"],
                    ),
                )
