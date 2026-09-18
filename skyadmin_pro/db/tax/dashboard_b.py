"""Database Tax operations."""

from __future__ import annotations

from datetime import date

from skyadmin_pro.db.sql_helpers import (
    _in_clause,
)


class DashboardMixinB:
    def dashboard_snapshot(self) -> dict:
        """Single refresh bundle - one pinned connection for all snapshot queries."""

        today = date.today()
        with self.bundle_queries():
            expiring = self.list_expiring_documents(exclude_expired=True)
            supplier_expiring = self.list_expiring_supplier_services()
            counts = self.dashboard_counts(
                expiring_total=len(expiring) + len(supplier_expiring), exclude_expired_tasks=True
            )
            return {
                "counts": counts,
                "expiring": expiring,
                "supplier_expiring": supplier_expiring,
                "overdue": self.list_overdue_services(),
                "supplier_due": self.list_pending_supplier_payments(),
                "pending": self.list_tasks(status="pending", exclude_expired=True),
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
              AND c.deleted_at IS NULL AND COALESCE(c.status, 'active') != 'inactive'
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
