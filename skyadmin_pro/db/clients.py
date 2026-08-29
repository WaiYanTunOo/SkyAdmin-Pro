"""Database Clients operations."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta

from skyadmin_pro.config import (
    NEW_CUSTOMER_QUOTATION_TASKS,
)
from skyadmin_pro.db.sql_helpers import (
    _escape_like,
    _in_clause,
)


class ClientsMixin:
    def list_client_names(self) -> list[str]:
        with self.connection() as conn:
            rows = conn.execute("SELECT name FROM clients ORDER BY name COLLATE NOCASE").fetchall()
        return [row["name"] for row in rows]

    def client_id_by_name(self, name: str) -> int | None:
        """Look up an existing client id without creating anything."""
        cleaned = (name or "").strip()
        if not cleaned:
            return None
        row = self._fetch_one("SELECT id FROM clients WHERE name = ? COLLATE NOCASE", (cleaned,))
        return int(row["id"]) if row else None

    def get_or_create_client(self, name: str) -> int:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Client name is required.")
        with self.connection() as conn:
            row = conn.execute(
                "SELECT id FROM clients WHERE name = ? COLLATE NOCASE",
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
            except sqlite3.IntegrityError:
                row = conn.execute(
                    "SELECT id FROM clients WHERE name = ? COLLATE NOCASE",
                    (cleaned,),
                ).fetchone()
                if row is None:
                    raise
                return int(row["id"])
        self.add_new_client_tasks(new_id, cleaned)
        self._organization_list_cache = None
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
        return rows

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

    def _fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def _fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        with self.connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return dict(row) if row is not None else None

    def list_clients(self) -> list[dict]:
        return self._fetch_all(
            """
            SELECT id, name, company_name, contact_name, email, status, notes,
                   registration_number, director, contact_number,
                   registered_capital, vat_registration, business_address,
                   business_objectives, created_at, updated_at
            FROM clients
            ORDER BY name COLLATE NOCASE
            """
        )

    def get_client(self, client_id: int) -> dict | None:
        row = self._fetch_one(
            "SELECT * FROM clients WHERE id = ?",
            (client_id,),
        )
        return self._prepare_client_record(row)

    def search_clients(self, query: str = "") -> list[dict]:
        """Company-list rows: match name / contact / email, sorted by name."""
        sql = """
            SELECT id, name, company_name, contact_name, email, status, notes,
                   registration_number, director, contact_number,
                   registered_capital, vat_registration, business_address,
                   business_objectives, created_at, updated_at
            FROM clients
        """
        params: tuple = ()
        q = (query or "").strip()
        if q:
            like = f"%{_escape_like(q)}%"
            sql += " WHERE name LIKE ? ESCAPE '\\' OR contact_name LIKE ? ESCAPE '\\' OR email LIKE ? ESCAPE '\\'"
            params = (like, like, like)
        sql += " ORDER BY name COLLATE NOCASE"
        return self._fetch_all(sql, params)

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
                        business_address = ?, business_objectives = ?, updated_at = ?
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
                        self._now(),
                        client_id,
                    ),
                )
            except sqlite3.IntegrityError:
                raise ValueError("A client with that name already exists.") from None

    def delete_client(self, client_id: int) -> None:
        with self.connection() as conn:
            conn.execute(
                "DELETE FROM tasks WHERE pipeline_item_id IN (SELECT id FROM pipeline_items WHERE client_id = ?)",
                (client_id,),
            )
            conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
