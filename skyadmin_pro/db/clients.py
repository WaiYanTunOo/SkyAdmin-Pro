"""Database Clients operations."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from skyadmin_pro.config import (
    NEW_CUSTOMER_QUOTATION_TASKS,
)
from skyadmin_pro.db.cipher import INTEGRITY_ERRORS
from skyadmin_pro.db.sql_helpers import (
    _escape_like,
    _in_clause,
)


class ClientsMixin:
    def list_client_names(self) -> list[str]:
        cached = getattr(self, "_client_names_cache", None)
        if cached is not None:
            return list(cached)
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT name FROM clients WHERE deleted_at IS NULL ORDER BY name COLLATE NOCASE"
            ).fetchall()
        names = [row["name"] for row in rows]
        self._client_names_cache = names
        return list(names)

    def invalidate_client_names_cache(self) -> None:
        self._client_names_cache = None

    def client_id_by_name(self, name: str) -> int | None:
        """Look up an existing (non-archived) client id without creating anything."""
        cleaned = (name or "").strip()
        if not cleaned:
            return None
        row = self._fetch_one(
            "SELECT id FROM clients WHERE name = ? COLLATE NOCASE AND deleted_at IS NULL",
            (cleaned,),
        )
        return int(row["id"]) if row else None

    def get_or_create_client(self, name: str) -> int:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Client name is required.")
        with self.connection() as conn:
            row = conn.execute(
                "SELECT id FROM clients WHERE name = ? COLLATE NOCASE AND deleted_at IS NULL",
                (cleaned,),
            ).fetchone()
            if row is not None:
                return int(row["id"])
            try:
                cursor = conn.execute(
                    "INSERT INTO clients (name) VALUES (?)",
                    (cleaned,),
                )
                new_id = int(cursor.lastrowid)
            except INTEGRITY_ERRORS:
                row = conn.execute(
                    "SELECT id FROM clients WHERE name = ? COLLATE NOCASE AND deleted_at IS NULL",
                    (cleaned,),
                ).fetchone()
                if row is None:
                    # Name may belong to an archived row — surface a clear error.
                    archived = conn.execute(
                        "SELECT id FROM clients WHERE name = ? COLLATE NOCASE",
                        (cleaned,),
                    ).fetchone()
                    if archived is not None:
                        raise ValueError(
                            "A client with that name is archived. Restore it or use a different name."
                        ) from None
                    raise
                return int(row["id"])
        self.add_new_client_tasks(new_id, cleaned)
        self._organization_list_cache = None
        self._client_names_cache = None
        return new_id

    def add_new_client_tasks(self, client_id: int, client_name: str) -> list[int]:
        """Auto-create quotation follow-up tasks for a brand-new customer."""
        today = date.today()
        return [
            self.add_task(
                title=title.replace("{client}", client_name),
                client_id=client_id,
                category=category,
                due_date=(today + timedelta(days=offset_days)).isoformat(),
            )
            for title, offset_days, category in NEW_CUSTOMER_QUOTATION_TASKS
        ]

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

    def set_document_paid(self, document_id: int, paid: bool = True) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE documents SET paid = ? WHERE id = ?",
                (1 if paid else 0, document_id),
            )

    def get_document(self, document_id: int) -> dict | None:
        return self._fetch_one(
            """
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.start_date, d.progress, d.file_name, d.file_path,
                   d.completed_at, d.created_at, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.id = ?
            """,
            (document_id,),
        )

    def list_client_services(self, client_id: int) -> list[dict]:
        clause, params = _in_clause("d.document_type", tuple(self.list_service_types()))
        return self._fetch_all(
            f"""
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.start_date, d.progress, d.paid, d.file_name, d.file_path,
                   d.completed_at, d.created_at, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.client_id = ? AND {clause}
            ORDER BY d.expiry_date IS NULL, d.expiry_date, d.id DESC
            """,
            (client_id, *params),
        )

    def list_incentive_services(self, year: int, month: int) -> list[dict]:
        """New services signed up during a given calendar month (incentive
        report).  Filters by start_date for documents (the actual service
        start date) and created_at for pipeline items (client appointment
        date)."""
        prefix = f"{year:04d}-{month:02d}"
        service_types = self.list_service_types()
        if service_types:
            doc_clause, doc_params = _in_clause("d.document_type", tuple(service_types))
            doc_sql = f"""
            SELECT d.id, 'doc' AS src, d.client_id, d.document_type AS service,
                   d.amount, d.start_date AS service_date,
                   c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.start_date IS NOT NULL
              AND d.start_date LIKE '{prefix}%'
              AND {doc_clause}
            """
        else:
            doc_sql = "SELECT NULL WHERE 1 = 0"
            doc_params = []

        pipe_sql = f"""
        SELECT p.id, 'pipe' AS src, p.client_id, p.service,
               NULL AS amount, p.created_at AS service_date,
               c.name AS client_name
        FROM pipeline_items p
        LEFT JOIN clients c ON c.id = p.client_id
        WHERE p.created_at LIKE '{prefix}%'
        """

        sql = f"{doc_sql} UNION ALL {pipe_sql} ORDER BY service_date ASC"
        rows = self._fetch_all(sql, tuple(doc_params))
        for row in rows:
            row["source"] = row["src"]
            row["id_key"] = f"{'doc' if row['src'] == 'doc' else 'pipe'}-{row['id']}"
            row["amount"] = self._resolve_incentive_amount(row.get("service"), row.get("amount"))
        return rows

    def _resolve_incentive_amount(self, service: str | None, doc_amount) -> str | int | None:
        """Amount for incentive report — document value, else pricing matrix headcount/fee."""
        if doc_amount not in (None, ""):
            return doc_amount
        service_name = (service or "").strip()
        if not service_name:
            return None
        tiers = self.get_pricing_matrix(service_type=service_name)
        if not tiers:
            tiers = self._fetch_all(
                """
                SELECT * FROM pricing_matrix
                WHERE lower(service_type) = lower(?)
                ORDER BY monthly_fee ASC
                LIMIT 1
                """,
                (service_name,),
            )
        if tiers:
            tier = tiers[0]
            return tier.get("headcount") or tier.get("monthly_fee")
        return None

    def list_client_documents(self, client_id: int) -> list[dict]:
        clause, params = _in_clause("d.document_type", tuple(self.list_service_types()))
        return self._fetch_all(
            f"""
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.start_date, d.progress, d.paid, d.file_name, d.file_path,
                   d.created_at, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.client_id = ? AND NOT {clause}
            ORDER BY d.created_at DESC, d.id DESC
            """,
            (client_id, *params),
        )

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def list_clients(self, *, limit: int | None = None, offset: int = 0) -> list[dict]:
        base = """
            SELECT id, name, company_name, contact_name, email, status, notes,
                   registration_number, director, contact_number,
                   registered_capital, vat_registration, business_address,
                   business_objectives, group_id, created_at, updated_at
            FROM clients
            WHERE deleted_at IS NULL
            ORDER BY name COLLATE NOCASE
            """
        if limit is not None and int(limit) > 0:
            return self._fetch_page(base, (), limit=limit, offset=offset)
        return self._fetch_all(base)

    def count_clients(self, query: str = "") -> int:
        q = (query or "").strip()
        if not q:
            row = self._fetch_one("SELECT COUNT(*) AS n FROM clients WHERE deleted_at IS NULL")
            return int(row["n"]) if row else 0
        # LIKE fallback count (FTS count would need MATCH sync; LIKE is safe).
        from skyadmin_pro.db.sql_helpers import _escape_like as _esc

        like = f"%{_esc(q)}%"
        row = self._fetch_one(
            "SELECT COUNT(*) AS n FROM clients"
            " WHERE deleted_at IS NULL"
            " AND (name LIKE ? ESCAPE '\\' OR contact_name LIKE ? ESCAPE '\\'"
            " OR email LIKE ? ESCAPE '\\')",
            (like, like, like),
        )
        return int(row["n"]) if row else 0

    def get_client(self, client_id: int) -> dict | None:
        row = self._fetch_one(
            "SELECT * FROM clients WHERE id = ?",
            (client_id,),
        )
        return self._prepare_client_record(row)

    def search_clients(self, query: str = "", *, limit: int | None = None, offset: int = 0) -> list[dict]:
        """Company-list rows: match name / contact / email, sorted by name."""
        base_select = """
            SELECT id, name, company_name, contact_name, email, status, notes,
                   registration_number, director, contact_number,
                   registered_capital, vat_registration, business_address,
                   business_objectives, group_id, created_at, updated_at
            FROM clients
            WHERE deleted_at IS NULL
        """
        q = (query or "").strip()
        if not q:
            base = base_select + " ORDER BY name COLLATE NOCASE"
            if limit is not None and int(limit) > 0:
                return self._fetch_page(base, (), limit=limit, offset=offset)
            return self._fetch_all(base)
        try:
            tokens = [t for t in q.split() if t]
            if tokens:
                fts_query = " ".join(f'"{t}"*' for t in tokens)
                base = """
                    SELECT c.id, c.name, c.company_name, c.contact_name, c.email, c.status, c.notes,
                           c.registration_number, c.director, c.contact_number,
                           c.registered_capital, c.vat_registration, c.business_address,
                           c.business_objectives, c.group_id, c.created_at, c.updated_at
                    FROM clients c
                    INNER JOIN clients_fts fts ON fts.rowid = c.id
                    WHERE fts MATCH ? AND c.deleted_at IS NULL
                    ORDER BY c.name COLLATE NOCASE
                    """
                if limit is not None and int(limit) > 0:
                    return self._fetch_page(base, (fts_query,), limit=limit, offset=offset)
                return self._fetch_all(base, (fts_query,))
        except Exception:
            self._log.debug("FTS search failed, falling back to LIKE", exc_info=True)
        like = f"%{_escape_like(q)}%"
        base = (
            base_select + " AND (name LIKE ? ESCAPE '\\' OR contact_name LIKE ? ESCAPE '\\'"
            " OR email LIKE ? ESCAPE '\\')" + " ORDER BY name COLLATE NOCASE"
        )
        if limit is not None and int(limit) > 0:
            return self._fetch_page(base, (like, like, like), limit=limit, offset=offset)
        return self._fetch_all(base, (like, like, like))

    def update_client(
        self,
        client_id: int,
        *,
        name: str | None = None,
        company_name: str | None = None,
        contact_name: str | None = None,
        email: str | None = None,
        notes: str | None = None,
        status: str | None = None,
        registration_number: str | None = None,
        director: str | None = None,
        contact_number: str | None = None,
        registered_capital: str | None = None,
        vat_registration: str | None = None,
        business_address: str | None = None,
        business_objectives: str | None = None,
        group_id: int | None = None,
        clear_group: bool = False,
    ) -> None:
        """Update a client. None keeps the current value; '' clears a text field."""
        if status is not None and status not in {"active", "inactive"}:
            raise ValueError("Status must be active or inactive.")
        current = self.get_client(client_id)
        if current is None:
            raise ValueError("Client not found.")
        new_name = (name if name is not None else current["name"]).strip()
        if not new_name:
            raise ValueError("Client name is required.")
        values = {
            "name": new_name,
            "company_name": company_name if company_name is not None else current["company_name"],
            "contact_name": contact_name if contact_name is not None else current["contact_name"],
            "email": email if email is not None else current["email"],
            "notes": notes if notes is not None else current["notes"],
            "status": status if status is not None else current["status"],
            "registration_number": (
                registration_number if registration_number is not None else current["registration_number"]
            ),
            "director": director if director is not None else current["director"],
            "contact_number": (contact_number if contact_number is not None else current["contact_number"]),
            "registered_capital": (
                registered_capital if registered_capital is not None else current["registered_capital"]
            ),
            "vat_registration": (vat_registration if vat_registration is not None else current["vat_registration"]),
            "business_address": (business_address if business_address is not None else current["business_address"]),
            "business_objectives": (
                business_objectives if business_objectives is not None else current["business_objectives"]
            ),
            "group_id": (None if clear_group else (group_id if group_id is not None else current.get("group_id"))),
        }
        with self.connection() as conn:
            try:
                conn.execute(
                    """
                    UPDATE clients
                    SET name = ?, company_name = ?, contact_name = ?, email = ?,
                        notes = ?, status = ?,
                        registration_number = ?, director = ?, contact_number = ?,
                        registered_capital = ?, vat_registration = ?,
                        business_address = ?, business_objectives = ?,
                        group_id = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        values["name"],
                        values["company_name"],
                        values["contact_name"],
                        values["email"],
                        values["notes"],
                        values["status"],
                        values["registration_number"],
                        values["director"],
                        values["contact_number"],
                        values["registered_capital"],
                        values["vat_registration"],
                        values["business_address"],
                        values["business_objectives"],
                        values["group_id"],
                        self._now(),
                        client_id,
                    ),
                )
            except INTEGRITY_ERRORS:
                raise ValueError("A client with that name already exists.") from None
        self._client_names_cache = None

    def delete_client(self, client_id: int) -> None:
        with self.connection() as conn:
            conn.execute(
                "DELETE FROM tasks WHERE pipeline_item_id IN (SELECT id FROM pipeline_items WHERE client_id = ?)",
                (client_id,),
            )
            conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        self._client_names_cache = None

    def batch_delete_clients(self, client_ids: list[int]) -> int:
        """Delete multiple clients and cascade-delete related tasks. Returns count deleted."""
        if not client_ids:
            return 0
        placeholders = ",".join("?" for _ in client_ids)
        with self.connection() as conn:
            conn.execute(
                f"DELETE FROM tasks WHERE pipeline_item_id IN (SELECT id FROM pipeline_items WHERE client_id IN ({placeholders}))",
                client_ids,
            )
            cursor = conn.execute(
                f"DELETE FROM clients WHERE id IN ({placeholders})",
                client_ids,
            )
            count = cursor.rowcount
        self._client_names_cache = None
        return count

    def batch_update_client_status(self, client_ids: list[int], status: str) -> int:
        """Update status for multiple clients. Returns count updated."""
        if not client_ids:
            return 0
        normalized = (status or "").strip().lower()
        if normalized not in {"active", "inactive"}:
            raise ValueError("Status must be active or inactive.")
        placeholders = ",".join("?" for _ in client_ids)
        with self.connection() as conn:
            cursor = conn.execute(
                f"UPDATE clients SET status = ?, updated_at = ? WHERE id IN ({placeholders}) AND deleted_at IS NULL",
                [normalized, self._now(), *client_ids],
            )
            count = cursor.rowcount
        self._client_names_cache = None
        return count

    def batch_assign_client_group(self, client_ids: list[int], group_id: int | None) -> int:
        """Assign (or clear) local group for multiple clients. Returns count updated.

        ``group_id`` is local-only and is never synced.
        """
        if not client_ids:
            return 0
        if group_id is not None:
            group = self._fetch_one("SELECT id FROM client_groups WHERE id = ?", (group_id,))
            if group is None:
                raise ValueError("Group not found.")
        placeholders = ",".join("?" for _ in client_ids)
        with self.connection() as conn:
            cursor = conn.execute(
                f"UPDATE clients SET group_id = ?, updated_at = ? WHERE id IN ({placeholders}) AND deleted_at IS NULL",
                [group_id, self._now(), *client_ids],
            )
            count = cursor.rowcount
        return count

    def batch_archive_clients(self, client_ids: list[int]) -> int:
        """Soft-delete clients by setting ``deleted_at``. Returns count archived."""
        if not client_ids:
            return 0
        now = self._now()
        placeholders = ",".join("?" for _ in client_ids)
        with self.connection() as conn:
            cursor = conn.execute(
                f"UPDATE clients SET deleted_at = ?, updated_at = ?"
                f" WHERE id IN ({placeholders}) AND deleted_at IS NULL",
                [now, now, *client_ids],
            )
            count = cursor.rowcount
        self._client_names_cache = None
        return count

    def batch_restore_clients(self, client_ids: list[int]) -> int:
        """Clear ``deleted_at`` for archived clients. Returns count restored."""
        if not client_ids:
            return 0
        placeholders = ",".join("?" for _ in client_ids)
        with self.connection() as conn:
            cursor = conn.execute(
                f"UPDATE clients SET deleted_at = NULL, updated_at = ?"
                f" WHERE id IN ({placeholders}) AND deleted_at IS NOT NULL",
                [self._now(), *client_ids],
            )
            count = cursor.rowcount
        self._client_names_cache = None
        return count

    # -- Client groups --------------------------------------------------

    def list_client_groups(self) -> list[dict]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, name, color, global_id
                FROM client_groups
                WHERE deleted_at IS NULL
                ORDER BY name COLLATE NOCASE
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def add_client_group(self, name: str, color: str | None = None) -> int:
        import uuid

        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("Group name is required.")
        with self.connection() as conn:
            try:
                cur = conn.execute(
                    """
                    INSERT INTO client_groups (name, color, global_id, updated_at)
                    VALUES (?, ?, ?, datetime('now', 'localtime'))
                    """,
                    (cleaned, color, uuid.uuid4().hex),
                )
            except INTEGRITY_ERRORS:
                raise ValueError("A group with that name already exists.") from None
        return int(cur.lastrowid)

    def update_client_group(self, group_id: int, name: str, color: str | None = None) -> int:
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("Group name is required.")
        with self.connection() as conn:
            try:
                cur = conn.execute(
                    """
                    UPDATE client_groups
                    SET name = ?, color = ?, updated_at = datetime('now', 'localtime')
                    WHERE id = ? AND deleted_at IS NULL
                    """,
                    (cleaned, color, group_id),
                )
            except INTEGRITY_ERRORS:
                raise ValueError("A group with that name already exists.") from None
        return cur.rowcount

    def delete_client_group(self, group_id: int) -> int:
        """Soft-delete a group (clients in it become ungrouped). Synced via deleted_at."""
        with self.connection() as conn:
            conn.execute("UPDATE clients SET group_id = NULL WHERE group_id = ?", (group_id,))
            cur = conn.execute(
                """
                UPDATE client_groups
                SET deleted_at = datetime('now', 'localtime'),
                    updated_at = datetime('now', 'localtime')
                WHERE id = ? AND deleted_at IS NULL
                """,
                (group_id,),
            )
        return cur.rowcount
