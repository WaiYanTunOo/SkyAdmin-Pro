"""Database Tasks operations."""

from __future__ import annotations

from skyadmin_pro.config import (
    EXPIRY_ALERT_DAYS,
    GENERAL_RENEWAL_TEMPLATE_NAME,
    renewal_template_for,
    service_task_category,
)
from skyadmin_pro.db.sql_helpers import (
    _expiry_type_condition,
    _expiry_window_condition,
    _in_clause,
)
from skyadmin_pro.services.tracking import days_until, effective_expiry_date


class TasksMixin:
    def list_tasks(self, status: str | None = None) -> list[dict]:
        sql = """
            SELECT t.id, t.client_id, t.title, t.description, t.status, t.category,
                   t.due_date, t.completed_at, t.created_at, t.updated_at,
                   t.pipeline_item_id, t.pipeline_step, t.source_document_id,
                   c.name AS client_name
            FROM tasks t
            LEFT JOIN clients c ON c.id = t.client_id
        """
        params: tuple = ()
        if status:
            sql += " WHERE t.status = ?"
            params = (status,)
        sql += """
            ORDER BY CASE t.status WHEN 'pending' THEN 0 ELSE 1 END,
                     CASE WHEN t.due_date IS NULL OR t.due_date = '' THEN 1 ELSE 0 END,
                     t.due_date,
                     t.id DESC
        """
        return self._fetch_all(sql, params)

    def get_task(self, task_id: int) -> dict | None:
        return self._fetch_one(
            """
            SELECT t.id, t.client_id, t.title, t.description, t.status, t.category,
                   t.due_date, t.completed_at, t.created_at, t.updated_at,
                   t.pipeline_item_id, t.pipeline_step, t.source_document_id,
                   c.name AS client_name
            FROM tasks t
            LEFT JOIN clients c ON c.id = t.client_id
            WHERE t.id = ?
            """,
            (task_id,),
        )

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
                    source_document_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    ) -> None:
        cleaned = title.strip()
        if not cleaned:
            raise ValueError("Task title is required.")
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET client_id = ?, title = ?, description = ?, category = ?,
                    due_date = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    client_id,
                    cleaned,
                    description.strip() or None,
                    category,
                    due_date,
                    self._now(),
                    task_id,
                ),
            )

    def set_task_status(self, task_id: int, status: str) -> None:
        if status not in {"pending", "completed"}:
            raise ValueError("Status must be pending or completed.")
        now = self._now()
        completed_at = now if status == "completed" else None
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, completed_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, completed_at, now, task_id),
            )

    def delete_task(self, task_id: int) -> None:
        with self.connection() as conn:
            # service_renewals.task_id CASCADEs on task delete — detach the
            # history row first so deleting a routine todo never destroys
            # the renewal audit trail.
            conn.execute(
                "UPDATE service_renewals SET task_id = NULL WHERE task_id = ?",
                (task_id,),
            )
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def sync_service_progress_task(self, document_id: int) -> None:
        """Keep one "Continue: <service>" task in step with a service's progress.

        Marking a service Ongoing creates (once) a pending task linked to the
        service record; marking it Completed completes that task, so ongoing
        work shows up in Tasks and on the Dashboard until it is finished.
        """
        doc = self._fetch_one(
            "SELECT id, client_id, document_type, progress FROM documents WHERE id = ?",
            (document_id,),
        )
        if not doc:
            return
        progress = (doc.get("progress") or "").strip()
        if progress == "Ongoing":
            linked = self._fetch_one("SELECT id FROM tasks WHERE source_document_id = ?", (document_id,))
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
                "SELECT id, status FROM tasks WHERE source_document_id = ?",
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
            WHERE t.status = 'completed'
              -- lexical compare on 'YYYY-MM-DD HH:MM:SS' keeps idx usable
              AND t.completed_at >= date('now', 'localtime')
              AND t.completed_at <  date('now', 'localtime', '+1 day')
            ORDER BY t.completed_at DESC
            """
        )

    def list_documents(self, *, expiring_only: bool = False) -> list[dict]:
        where = ""
        if expiring_only:
            # Lets idx_documents_expiry drive the filter instead of loading
            # the whole table and discarding rows in Python. Orphaned records
            # (client deleted) are excluded — they have nobody to alert.
            where = "WHERE d.expiry_date IS NOT NULL AND trim(d.expiry_date) != '' AND d.client_id IS NOT NULL"
        return self._fetch_all(
            f"""
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.start_date, d.file_name, d.file_path, d.created_at,
                   c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            {where}
            ORDER BY d.expiry_date IS NULL, d.expiry_date, d.id DESC
            """
        )

    def list_expiring_documents(self) -> list[dict]:
        rows = self._fetch_all(
            f"""
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.progress, d.paid, d.file_name, d.file_path,
                   d.created_at, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.client_id IS NOT NULL
              AND d.expiry_date IS NOT NULL AND trim(d.expiry_date) != ''
              AND d.document_type IS NOT NULL AND trim(d.document_type) != ''
              AND {_expiry_type_condition("d.document_type", tuple(self.list_service_types()))}
              AND {_expiry_window_condition("d.document_type", "d.expiry_date")}
            ORDER BY d.expiry_date ASC
            """
        )
        # Re-check against the EFFECTIVE expiry date: an annual service stored
        # as 2025-12-31 is active until the next 31 December, so it must not
        # alert when it effectively has more than EXPIRY_ALERT_DAYS left.
        filtered = []
        for row in rows:
            effective = effective_expiry_date(row["expiry_date"], row["document_type"])
            left = days_until(effective)
            if left is not None and left <= EXPIRY_ALERT_DAYS:
                filtered.append(row)
        return filtered

    def list_ongoing_services(self) -> list[dict]:
        """Every service currently marked Ongoing, newest started first."""
        clause, params = _in_clause("d.document_type", tuple(self.list_service_types()))
        return self._fetch_all(
            f"""
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.start_date, d.progress, d.paid,
                   d.created_at, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.client_id IS NOT NULL AND d.progress = 'Ongoing'
              AND {clause}
            ORDER BY d.start_date IS NULL, d.start_date DESC, d.id DESC
            """,
            tuple(params),
        )

    def list_renewal_items_due(self) -> list[dict]:
        """Renewal checklist items that are due but not yet done.

        One row per (client, template) that has a matching expiring service:
        template, how many items are due, and the nearest expiry driving them.
        Uses three bulk queries (items, services, clients) and groups in
        Python instead of querying per client.
        """
        all_items = self._fetch_all("SELECT client_id, template_name, item, due_days, done FROM renewal_items")
        if not all_items:
            return []
        service_types = tuple(self.list_service_types())
        clause, params = _in_clause("d.document_type", service_types)
        services = self._fetch_all(
            f"""
            SELECT d.client_id, d.document_type, d.expiry_date, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.client_id IS NOT NULL AND trim(d.expiry_date) != '' AND {clause}
            """,
            tuple(params),
        )
        # nearest (days_left, expiry, doc_type) per (client_id, template)
        best_by_key: dict[tuple[int, str], tuple[int, str, str]] = {}
        client_names: dict[int, str] = {}
        for svc in services:
            mapped = renewal_template_for(svc["document_type"]) or GENERAL_RENEWAL_TEMPLATE_NAME
            eff = effective_expiry_date(svc["expiry_date"], svc["document_type"])
            left = days_until(eff)
            if left is None:
                continue
            key = (svc["client_id"], mapped)
            current = best_by_key.get(key)
            if current is None or left < current[0]:
                best_by_key[key] = (left, eff, svc["document_type"])
            client_names[svc["client_id"]] = svc["client_name"] or ""

        pending_by_key: dict[tuple[int, str], list[dict]] = {}
        for item in all_items:
            if item["done"]:
                continue
            pending_by_key.setdefault((item["client_id"], item["template_name"]), []).append(item)

        results: list[dict] = []
        for (client_id, template_name), pending in pending_by_key.items():
            best = best_by_key.get((client_id, template_name))
            if best is None:
                continue
            left, expiry, doc_type = best
            due_items = [i for i in pending if left <= i["due_days"]]
            if not due_items:
                continue
            results.append(
                {
                    "client_id": client_id,
                    "client_name": client_names.get(client_id, ""),
                    "template_name": template_name,
                    "document_type": doc_type,
                    "expiry_date": expiry,
                    "days_left": left,
                    "due_count": len(due_items),
                }
            )
        results.sort(key=lambda row: row["days_left"])
        return results

    def delete_document(self, document_id: int) -> None:
        with self.connection() as conn:
            task_ids = [
                row["task_id"]
                for row in conn.execute(
                    "SELECT task_id FROM service_renewals WHERE service_id = ? AND task_id IS NOT NULL",
                    (document_id,),
                ).fetchall()
            ]
            if task_ids:
                placeholders = ", ".join("?" for _ in task_ids)
                conn.execute(f"DELETE FROM tasks WHERE id IN ({placeholders})", task_ids)
            conn.execute("DELETE FROM tasks WHERE source_document_id = ?", (document_id,))
            conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))

    # ------------------------------------------------------------------ #
    # Service renewal / extension records
    # ------------------------------------------------------------------ #
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
