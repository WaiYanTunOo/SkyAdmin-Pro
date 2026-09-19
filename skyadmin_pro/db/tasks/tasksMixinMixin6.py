from __future__ import annotations


class TasksMixinMixin6:
    def renewal_docs_default(self, client_id: int, document_type: str) -> bool:
        """Per-company + service preference: what the last renewal chose.

        Whether documents are needed varies by company and by time (e.g. a
        CSH extension may need none today but documents later). Falls back to
        True (needs documents) when there is no history yet.
        """
        row = self._fetch_one(
            """
            SELECT needs_documents FROM service_renewals
            WHERE client_id = ? AND document_type = ?
            ORDER BY created_at DESC, id DESC LIMIT 1
            """,
            (client_id, document_type),
        )
        return bool(row["needs_documents"]) if row else True

    def list_service_renewals(self, service_id: int) -> list[dict]:
        return self._fetch_all(
            """
            SELECT * FROM service_renewals
            WHERE service_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (service_id,),
        )

    def all_service_renewals(self) -> list[dict]:
        """Every renewal-history row with client + service names (for export)."""
        return self._fetch_all(
            """
            SELECT c.name AS client_name, sr.document_type,
                   sr.previous_expiry, sr.new_expiry, sr.note,
                   sr.needs_documents, sr.created_at AS renewed_at
            FROM service_renewals sr
            LEFT JOIN clients c ON c.id = sr.client_id
            ORDER BY sr.created_at DESC, sr.id DESC
            """
        )

    def list_client_renewals(self, client_id: int) -> list[dict]:
        return self._fetch_all(
            """
            SELECT * FROM service_renewals
            WHERE client_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (client_id,),
        )

    def generate_recurring_tasks(self) -> int:
        """Scan recurring_tasks and generate tasks that are due."""
        with self.connection() as conn:
            cols = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='recurring_tasks'"
            ).fetchone()
            if not cols:
                return 0
            now = self._now()
            rows = conn.execute(
                """
                SELECT id, client_id, title_template, category
                FROM recurring_tasks
                WHERE deleted_at IS NULL
                  AND (last_generated IS NULL OR last_generated < date('now', 'start of month'))
                """
            ).fetchall()
            created = 0
            for row in rows:
                title = f"{row['title_template']} - {now[:7]}"
                conn.execute(
                    """
                    INSERT INTO tasks (client_id, title, category, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (row["client_id"], title, row["category"], now, now),
                )
                conn.execute(
                    "UPDATE recurring_tasks SET last_generated = ? WHERE id = ?",
                    (now, row["id"]),
                )
                created += 1
            return created

    def _TasksMixin_record_service_renewal_p1(self, service_id, new_expiry, needs_documents):
        service = self.get_document(service_id)
        if service is None:
            raise ValueError("Service record not found.")
        new_expiry = (new_expiry or "").strip()
        if not new_expiry:
            raise ValueError("Enter the new expiry date.")
        needs_documents = bool(needs_documents)
        now = self._now()
        doc_type = service.get("document_type") or "Service"
        title = f"Renew / extend {doc_type}"
        description = (
            "Documents required for this renewal." if needs_documents else "No documents required for this renewal."
        )
        category = "Visa" if any(key in doc_type for key in ("Visa", "Passport", "Work Permit", "Non-B")) else "General"
        return category, description, doc_type, needs_documents, new_expiry, now, service, title
