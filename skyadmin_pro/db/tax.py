"""Database Tax operations."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from skyadmin_pro.config import (
    MONTHLY_TAX_TYPES,
    RENEWAL_CHECKLIST_ITEMS,
)
from skyadmin_pro.db.sql_helpers import (
    _in_clause,
)
from skyadmin_pro.services.tracking import effective_expiry_date


class TaxMixin:
    def set_client_month_status(self, client_id: int, month_key: str, status: str, note: str = "") -> None:
        if status not in {"open", "in_progress", "closed"}:
            raise ValueError("Status must be open, in_progress or closed.")
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO client_months (client_id, month_key, status, note, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(client_id, month_key) DO UPDATE SET
                    status = excluded.status,
                    note = excluded.note,
                    updated_at = excluded.updated_at
                """,
                (client_id, month_key, status, (note or "").strip() or None, self._now()),
            )

    def list_client_month_status(self, month_key: str) -> dict[int, dict]:
        rows = self._fetch_all(
            """
            SELECT client_id, status, note, updated_at
            FROM client_months
            WHERE month_key = ?
            """,
            (month_key,),
        )
        return {int(row["client_id"]): row for row in rows}

    def list_monthly_tax_clients(self) -> list[dict]:
        """Clients with an active monthly tax / month-close service."""
        return self._fetch_all(
            f"""
            SELECT DISTINCT c.id, c.name
            FROM clients c
            JOIN documents d ON d.client_id = c.id
            WHERE d.document_type IN ({", ".join("?" for _ in MONTHLY_TAX_TYPES)})
            ORDER BY c.name COLLATE NOCASE
            """,
            tuple(MONTHLY_TAX_TYPES),
        )

    def month_close_summary(self, month_key: str, client_ids: list[int] | None = None) -> dict[str, int]:
        if client_ids is None:
            with self.connection() as conn:
                total = conn.execute("SELECT COUNT(*) AS n FROM clients").fetchone()["n"]
                closed = conn.execute(
                    """
                    SELECT COUNT(*) AS n FROM client_months
                    WHERE month_key = ? AND status = 'closed'
                    """,
                    (month_key,),
                ).fetchone()["n"]
                in_progress = conn.execute(
                    """
                    SELECT COUNT(*) AS n FROM client_months
                    WHERE month_key = ? AND status = 'in_progress'
                    """,
                    (month_key,),
                ).fetchone()["n"]
        else:
            scope = sorted(set(int(cid) for cid in client_ids))
            total = len(scope)
            closed = in_progress = 0
            if scope:
                placeholders = ", ".join("?" for _ in scope)
                with self.connection() as conn:
                    rows = conn.execute(
                        f"""
                        SELECT status, COUNT(*) AS n FROM client_months
                        WHERE month_key = ? AND client_id IN ({placeholders})
                        GROUP BY status
                        """,
                        (month_key, *scope),
                    ).fetchall()
                by_status = {row["status"]: row["n"] for row in rows}
                closed = int(by_status.get("closed", 0))
                in_progress = int(by_status.get("in_progress", 0))
        return {
            "clients": int(total),
            "closed": int(closed),
            "in_progress": int(in_progress),
            "open": max(0, int(total) - int(closed) - int(in_progress)),
        }

    def dashboard_counts(self, *, expiring_total: int | None = None) -> dict[str, int]:
        # Resolve helpers BEFORE opening the connection so they don't nest
        # additional connections inside this one.
        if expiring_total is None:
            expiring = len(self.list_expiring_documents()) + len(self.list_expiring_supplier_services())
        else:
            expiring = int(expiring_total)
        service_types = tuple(self.list_service_types())
        overdue_clause, overdue_params = _in_clause("document_type", service_types)
        with self.connection() as conn:
            pending = conn.execute("SELECT COUNT(*) AS n FROM tasks WHERE status = 'pending'").fetchone()["n"]
            done_today = conn.execute(
                """
                SELECT COUNT(*) AS n FROM tasks
                WHERE status = 'completed'
                  AND date(completed_at) = date('now', 'localtime')
                """
            ).fetchone()["n"]
            clients = conn.execute("SELECT COUNT(*) AS n FROM clients").fetchone()["n"]
            overdue = conn.execute(
                f"""
                SELECT COUNT(*) AS n FROM documents
                WHERE client_id IS NOT NULL
                  AND payment_date IS NOT NULL AND trim(payment_date) != ''
                  AND payment_date < date('now', 'localtime')
                  AND COALESCE(paid, 0) = 0
                  AND {overdue_clause}
                """,
                tuple(overdue_params),
            ).fetchone()["n"]
            supplier_due = conn.execute(
                """
                SELECT COUNT(*) AS n FROM supplier_payments
                WHERE paid = 0
                  AND due_date IS NOT NULL AND trim(due_date) != ''
                  AND date(due_date) < date('now', 'localtime')
                """
            ).fetchone()["n"]
            ongoing_clause, ongoing_params = _in_clause("document_type", service_types)
            ongoing = conn.execute(
                f"""
                SELECT COUNT(*) AS n FROM documents
                WHERE client_id IS NOT NULL AND progress = 'Ongoing'
                  AND {ongoing_clause}
                """,
                tuple(ongoing_params),
            ).fetchone()["n"]
        return {
            "pending": int(pending),
            "completed_today": int(done_today),
            "clients": int(clients),
            "expiring": int(expiring),
            "overdue": int(overdue),
            "supplier_due": int(supplier_due),
            "ongoing": int(ongoing),
        }

    def dashboard_snapshot(self) -> dict:
        """Single refresh bundle — one pinned connection for all snapshot queries."""
        from datetime import date

        today = date.today()
        with self.bundle_queries():
            expiring = self.list_expiring_documents()
            supplier_expiring = self.list_expiring_supplier_services()
            counts = self.dashboard_counts(expiring_total=len(expiring) + len(supplier_expiring))
            return {
                "counts": counts,
                "expiring": expiring,
                "supplier_expiring": supplier_expiring,
                "overdue": self.list_overdue_services(),
                "supplier_due": self.list_pending_supplier_payments(),
                "pending": self.list_tasks(status="pending"),
                "ongoing": self.list_ongoing_services(),
                "renewal_due": self.list_renewal_items_due(),
                "pending_filings": self.count_pending_filings(),
                "revenue": self.get_revenue_summary(today.year, today.month),
                "vo_csh_expiring": self.count_vo_csh_expiring(30),
                "accounting_clients": self.list_accounting_clients(),
            }

    def list_overdue_services(self) -> list[dict]:
        clause, params = _in_clause("d.document_type", tuple(self.list_service_types()))
        return self._fetch_all(
            f"""
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.progress, d.paid, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.client_id IS NOT NULL
              AND d.payment_date IS NOT NULL AND trim(d.payment_date) != ''
              AND date(d.payment_date) < date('now', 'localtime')
              AND COALESCE(d.paid, 0) = 0
              AND {clause}
            ORDER BY d.payment_date ASC
            """,
            tuple(params),
        )

    def next_invoice_number(self, client_id: int, month_key: str) -> str:
        """INV{YYYYMM}{NN} — next sequential number for a client's invoices.

        MAX-based (not COUNT): deleting an earlier invoice of the month no
        longer recycles its number, so issued numbers stay unique.
        """
        import re

        rows = self._fetch_all(
            """
            SELECT file_name FROM documents
            WHERE client_id = ? AND document_type = 'Invoice' AND file_name LIKE ?
            """,
            (client_id, f"{month_key}%"),
        )
        pattern = re.compile(rf"INV{re.escape(month_key)}(\d+)")
        highest = 0
        for row in rows:
            match = pattern.search(row["file_name"] or "")
            if match:
                highest = max(highest, int(match.group(1)))
        return f"{month_key}{highest + 1:02d}"

    def ensure_renewal_checklist(self, client_id: int, template_name: str | None = None) -> None:
        """Seed a client's renewal checklist for one template.

        Falls back to the built-in Visa Renewal list when no template name is
        given. Existing items are kept (INSERT OR IGNORE) so completed work is
        never lost when a template changes.
        """
        if template_name is None:
            template_name = "Visa Renewal"
        items = self.get_checklist_template_items(template_name)
        if not items:
            items = [{"item": item, "due_days": int(due_days)} for item, due_days in RENEWAL_CHECKLIST_ITEMS]
        with self.connection() as conn:
            for entry in items:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO renewal_items
                        (client_id, template_name, item, due_days)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        client_id,
                        template_name,
                        entry.get("item"),
                        int(entry.get("due_days") or 0),
                    ),
                )

    def list_renewal_checklist(self, client_id: int, template_name: str = "Visa Renewal") -> list[dict]:
        return self._fetch_all(
            """
            SELECT id, client_id, template_name, item, due_days, done, done_at
            FROM renewal_items
            WHERE client_id = ? AND template_name = ?
            ORDER BY due_days DESC, id ASC
            """,
            (client_id, template_name),
        )

    def set_renewal_item_done(self, item_id: int, done: bool) -> None:
        done_at = self._now() if done else None
        with self.connection() as conn:
            conn.execute(
                "UPDATE renewal_items SET done = ?, done_at = ? WHERE id = ?",
                (1 if done else 0, done_at, item_id),
            )

    def renewal_checklist_progress(self, client_id: int, template_name: str = "Visa Renewal") -> tuple[int, int]:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total,
                       COALESCE(SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END), 0) AS done
                FROM renewal_items WHERE client_id = ? AND template_name = ?
                """,
                (client_id, template_name),
            ).fetchone()
        return int(row["done"]), int(row["total"])

    # ------------------------------------------------------------------ #
    # Client fields: tax identity, filing statuses, VO & CSH, pricing
    # ------------------------------------------------------------------ #
    def update_client_fields(self, client_id: int, **fields: object) -> None:
        """Bulk-update any set of client columns. Only provided fields are changed."""
        allowed = {
            "tax_id",
            "ird_password",
            "vat_registered",
            "vat_registered_date",
            "service_type",
            "num_transactions",
            "service_fee",
            "payment_status",
            "sla",
            "headcount",
            "fs_status",
            "pnd53_status",
            "pp30_status",
            "pnd51_status",
            "pnd50_status",
            "audit_status",
            "vo_address",
            "vo_service_provider",
            "vo_renewal_date",
            "csh_service_provider",
            "csh_renewal_date",
            "shareholder_info",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        if "ird_password" in updates:
            from skyadmin_pro.services.secret_fields import encrypt_secret

            raw = str(updates["ird_password"] or "").strip()
            updates["ird_password"] = encrypt_secret(raw) if raw else ""
        sets = ", ".join(f"{k} = ?" for k in updates)
        params = list(updates.values()) + [self._now(), client_id]
        with self.connection() as conn:
            conn.execute(
                f"UPDATE clients SET {sets}, updated_at = ? WHERE id = ?",
                tuple(params),
            )

    def log_tax_change(self, client_id: int, field: str, old_value: str | None, new_value: str | None) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO tax_cycle_log (client_id, field, old_value, new_value, changed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (client_id, field, old_value, new_value, self._now()),
            )

    def get_client_tax_summary(self, client_id: int) -> dict[str, str]:
        client = self.get_client(client_id)
        if client is None:
            return {}
        return {
            "fs_status": client.get("fs_status") or "Not Applicable",
            "pnd53_status": client.get("pnd53_status") or "Not Applicable",
            "pp30_status": client.get("pp30_status") or "Not Applicable",
            "pnd51_status": client.get("pnd51_status") or "Not Applicable",
            "pnd50_status": client.get("pnd50_status") or "Not Applicable",
            "audit_status": client.get("audit_status") or "Not Applicable",
        }

    def list_clients_by_filing_status(self, field: str, status: str) -> list[dict]:
        if field not in {
            "fs_status",
            "pnd53_status",
            "pp30_status",
            "pnd51_status",
            "pnd50_status",
            "audit_status",
        }:
            return []
        return self._fetch_all(
            f"SELECT id, name FROM clients WHERE {field} = ? ORDER BY name COLLATE NOCASE",
            (status,),
        )

    def get_filing_change_history(self, client_id: int, limit: int = 20) -> list[dict]:
        """Return recent filing-status changes for a client, newest first."""
        return self._fetch_all(
            """
            SELECT id, field, old_value, new_value, changed_at
            FROM tax_cycle_log
            WHERE client_id = ?
            ORDER BY changed_at DESC, id DESC
            LIMIT ?
            """,
            (client_id, limit),
        )

    def get_filing_last_changed(self, client_id: int) -> str | None:
        """Return the most recent filing change timestamp for a client."""
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT changed_at FROM tax_cycle_log
                WHERE client_id = ?
                ORDER BY changed_at DESC, id DESC
                LIMIT 1
                """,
                (client_id,),
            ).fetchone()
        return row["changed_at"] if row else None

    def list_accounting_setup_candidates(self) -> list[dict]:
        """Clients with accounting documents and/or an accounting service contract."""
        from skyadmin_pro.config import ACCOUNTING_DOCUMENT_TYPES

        clause, params = _in_clause("d.document_type", tuple(ACCOUNTING_DOCUMENT_TYPES))
        rows = self._fetch_all(
            f"""
            SELECT c.id, c.name, c.tax_id, c.service_type, c.num_transactions,
                   c.service_fee, c.payment_status,
                   GROUP_CONCAT(DISTINCT d.document_type) AS document_types
            FROM clients c
            INNER JOIN documents d ON d.client_id = c.id
            WHERE {clause}
            GROUP BY c.id
            ORDER BY c.name COLLATE NOCASE
            """,
            params,
        )
        seen = {int(row["id"]) for row in rows}
        for row in self._fetch_all(
            """
            SELECT id, name, tax_id, service_type, num_transactions,
                   service_fee, payment_status, '' AS document_types
            FROM clients
            WHERE service_type IS NOT NULL AND trim(service_type) != ''
            ORDER BY name COLLATE NOCASE
            """
        ):
            if int(row["id"]) not in seen:
                rows.append(row)
                seen.add(int(row["id"]))
        return rows

    def list_accounting_clients(self) -> list[dict]:
        """Clients with service_type set (accounting service clients)."""
        return self._fetch_all(
            """
            SELECT id, name, service_type, num_transactions, service_fee,
                   payment_status, sla, headcount,
                   fs_status, pnd53_status, pp30_status,
                   pnd51_status, pnd50_status, audit_status,
                   vo_renewal_date, csh_renewal_date
            FROM clients
            WHERE service_type IS NOT NULL AND service_type != ''
            ORDER BY name COLLATE NOCASE
            """
        )

    def count_pending_filings(self) -> int:
        """Count of clients where any filing status = 'Pending'."""
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS n FROM clients
                WHERE fs_status = 'Pending' OR pnd53_status = 'Pending'
                   OR pp30_status = 'Pending' OR pnd51_status = 'Pending'
                   OR pnd50_status = 'Pending' OR audit_status = 'Pending'
                """
            ).fetchone()
        return int(row["n"])

    def get_revenue_summary(self, year: int, month: int) -> int:
        """Sum of service fees for clients with payment_status = 'Paid'
        and service_type set, filtered to the given year/month by created_at."""
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(CAST(REPLACE(service_fee, ',', '') AS INTEGER)), 0) AS total
                FROM clients
                WHERE payment_status = 'Paid'
                  AND service_fee IS NOT NULL AND service_fee != ''
                  AND service_type IS NOT NULL AND service_type != ''
                  AND strftime('%Y', created_at) = ?
                  AND strftime('%m', created_at) = ?
                """,
                (str(year), str(month).zfill(2)),
            ).fetchone()
        return int(row["total"])

    def roll_forward_stale_expiry_dates(self) -> int:
        """Persist rolled 31-Dec annual expiry dates so lists/exports match the dashboard."""

        rows = self._fetch_all(
            """
            SELECT id, document_type, expiry_date
            FROM documents
            WHERE expiry_date IS NOT NULL AND trim(expiry_date) != ''
            """
        )
        # Collect updates to apply in a single transaction
        updates: list[tuple[str, int]] = []
        for row in rows:
            effective = effective_expiry_date(row["expiry_date"], row["document_type"])
            if effective and effective != row["expiry_date"]:
                updates.append((effective, int(row["id"])))

        if not updates:
            return 0

        with self.connection() as conn:
            conn.executemany(
                "UPDATE documents SET expiry_date = ? WHERE id = ?",
                updates,
            )
        return len(updates)

    def count_vo_csh_expiring(self, days: int = 30) -> int:
        """Count of clients with VO or CSH renewal within N days."""
        with self.connection() as conn:
            row = conn.execute(
                f"""
                SELECT COUNT(*) AS n FROM clients
                WHERE (vo_renewal_date IS NOT NULL AND vo_renewal_date != ''
                       AND date(vo_renewal_date) <= date('now', 'localtime', '+{int(days)} days')
                       AND date(vo_renewal_date) >= date('now', 'localtime'))
                   OR (csh_renewal_date IS NOT NULL AND csh_renewal_date != ''
                       AND date(csh_renewal_date) <= date('now', 'localtime', '+{int(days)} days')
                       AND date(csh_renewal_date) >= date('now', 'localtime'))
                """
            ).fetchone()
        return int(row["n"])

    def create_vo_csh_renewal(self, client_id: int, renewal_type: str, renewal_date: str) -> int | None:
        """Auto-create a renewal item + task for VO or CSH renewal.

        *renewal_type* is ``"vo"`` or ``"csh"``.
        If a renewal item for this client+template already exists, its due date
        is updated instead of duplicating.  Returns the renewal item id, or
        *None* when *renewal_date* is empty.
        """
        if not renewal_date or not renewal_date.strip():
            return None
        template = "VO Renewal" if renewal_type == "vo" else "CSH Renewal"
        label = "VO" if renewal_type == "vo" else "CSH"
        client = self.get_client(client_id)
        client_name = (client or {}).get("name") or "client"
        # Due date = renewal_date minus 30 days. Strict parse: a garbage date
        # must fail loudly, never silently poison due-date sorting/alerts.
        try:
            due = (date.fromisoformat(renewal_date.strip()) - timedelta(days=30)).isoformat()
        except ValueError as exc:
            raise ValueError(f"Invalid renewal date: {renewal_date!r}") from exc
        # Upsert renewal item + create/update the reminder task in ONE
        # transaction so a crash can't leave an item without its task.
        task_title = f"Renew {label} for {client_name}"
        with self.connection() as conn:
            existing = conn.execute(
                "SELECT id FROM renewal_items WHERE client_id = ? AND template_name = ? LIMIT 1",
                (client_id, template),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE renewal_items SET due_days = 0, done = 0, done_at = NULL WHERE id = ?",
                    (existing["id"],),
                )
                renewal_item_id = existing["id"]
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO renewal_items (client_id, template_name, item, due_days)
                    VALUES (?, ?, ?, 0)
                    """,
                    (client_id, template, f"{label} renewal for {client_name}"),
                )
                renewal_item_id = cursor.lastrowid
            existing_task = conn.execute(
                "SELECT id FROM tasks WHERE client_id = ? AND title = ? AND status = 'pending' LIMIT 1",
                (client_id, task_title),
            ).fetchone()
            if existing_task:
                conn.execute(
                    "UPDATE tasks SET due_date = ?, updated_at = ? WHERE id = ?",
                    (due, self._now(), existing_task["id"]),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO tasks (client_id, title, description, status, category, due_date, created_at, updated_at)
                    VALUES (?, ?, ?, 'pending', 'General', ?, ?, ?)
                    """,
                    (client_id, task_title, f"Auto-created: {label} renewal due {due}", due, self._now(), self._now()),
                )
        return renewal_item_id

    def delete_vo_csh_renewal(self, client_id: int, renewal_type: str) -> None:
        """Remove renewal item and pending task for VO/CSH when date is cleared."""
        template = "VO Renewal" if renewal_type == "vo" else "CSH Renewal"
        label = "VO" if renewal_type == "vo" else "CSH"
        client = self.get_client(client_id)
        client_name = (client or {}).get("name") or "client"
        task_title = f"Renew {label} for {client_name}"
        with self.connection() as conn:
            conn.execute(
                "DELETE FROM renewal_items WHERE client_id = ? AND template_name = ?",
                (client_id, template),
            )
            conn.execute(
                "DELETE FROM tasks WHERE client_id = ? AND title = ? AND status = 'pending'",
                (client_id, task_title),
            )

    def run_monthly_cycle(self) -> dict:
        """Run monthly tax-cycle automation.

        For every client with ``service_type`` in ``MONTHLY_TAX_TYPES``, any
        filing status that is ``'Pending'`` is flipped to ``'On-Going'`` and a
        task is created.  The whole run is one transaction: either every
        client updates or none do.  Returns a summary dict.
        """
        from skyadmin_pro.config import MONTHLY_TAX_TYPES, TAX_FILING_FIELDS, TAX_FILING_LABELS

        clients = self._fetch_all(
            """
            SELECT id, name, fs_status, pnd53_status, pp30_status,
                   pnd51_status, pnd50_status, audit_status
            FROM clients
            WHERE service_type IN ({}) """.format(",".join("?" for _ in MONTHLY_TAX_TYPES)),
            tuple(MONTHLY_TAX_TYPES),
        )
        clients_processed = 0
        tasks_created = 0
        fields_updated = 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.connection() as conn:
            for client in clients:
                cid = client["id"]
                client_name = client.get("name") or "client"
                changed = False
                for field in TAX_FILING_FIELDS:
                    if client.get(field) == "Pending":
                        label = TAX_FILING_LABELS.get(field, field)
                        conn.execute(
                            f"UPDATE clients SET {field} = 'On-Going', updated_at = ? WHERE id = ?",
                            (now, cid),
                        )
                        conn.execute(
                            "INSERT INTO tax_cycle_log (client_id, field, old_value, new_value) "
                            "VALUES (?, ?, 'Pending', 'On-Going')",
                            (cid, field),
                        )
                        conn.execute(
                            """
                            INSERT INTO tasks (title, status, category, description,
                                               due_date, client_id, created_at, updated_at)
                            VALUES (?, 'pending', 'General', ?, ?, ?, ?, ?)
                            """,
                            (
                                f"Tax filing: {label} — {client_name}",
                                "Auto-created by monthly cycle. Status changed from Pending to On-Going.",
                                date.today().isoformat(),
                                cid,
                                now,
                                now,
                            ),
                        )
                        fields_updated += 1
                        tasks_created += 1
                        changed = True
                if changed:
                    clients_processed += 1
        return {
            "clients_processed": clients_processed,
            "tasks_created": tasks_created,
            "fields_updated": fields_updated,
        }

    # ------------------------------------------------------------------ #
    # Pricing matrix CRUD
    # ------------------------------------------------------------------ #
