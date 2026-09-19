"""Database Tax operations."""

from __future__ import annotations

from skyadmin_pro.config import PIPELINE_MAX_STEP
from skyadmin_pro.db.sql_helpers import (
    _in_clause,
)


class DashboardMixinA:
    def dashboard_counts(
        self, *, expiring_total: int | None = None, exclude_expired_tasks: bool = False
    ) -> dict[str, int]:
        # Resolve helpers BEFORE opening the connection so they don't nest
        # additional connections inside this one.
        if expiring_total is None:
            expiring = len(self.list_expiring_documents(exclude_expired=exclude_expired_tasks)) + len(
                self.list_expiring_supplier_services()
            )
        else:
            expiring = int(expiring_total)
        service_types = tuple(self.list_service_types())
        overdue_clause, overdue_params = _in_clause("document_type", service_types)

        with self.connection() as conn:
            pending_sql = """
                SELECT COUNT(*) AS n FROM tasks t
                LEFT JOIN clients c ON c.id = t.client_id
                WHERE t.status = 'pending' AND t.deleted_at IS NULL
                  AND (t.client_id IS NULL OR (c.deleted_at IS NULL AND COALESCE(c.status, 'active') != 'inactive'))
            """
            if exclude_expired_tasks:
                pending_sql += " AND (t.due_date IS NULL OR t.due_date >= date('now', 'localtime'))"
            pending = conn.execute(pending_sql).fetchone()["n"]

            done_today = conn.execute(
                """
                SELECT COUNT(*) AS n FROM tasks
                WHERE status = 'completed' AND deleted_at IS NULL
                  AND date(completed_at) = date('now', 'localtime')
                """
            ).fetchone()["n"]
            clients = conn.execute("SELECT COUNT(*) AS n FROM clients WHERE deleted_at IS NULL").fetchone()["n"]
            overdue = conn.execute(
                f"""
                SELECT COUNT(*) AS n FROM documents
                WHERE deleted_at IS NULL AND client_id IS NOT NULL
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
                WHERE deleted_at IS NULL AND paid = 0
                  AND due_date IS NOT NULL AND trim(due_date) != ''
                  AND date(due_date) < date('now', 'localtime')
                """
            ).fetchone()["n"]
            # Ongoing services = Service Pipeline items not yet at Completed step.
            ongoing = conn.execute(
                """
                SELECT COUNT(*) AS n FROM pipeline_items p
                LEFT JOIN clients c ON c.id = p.client_id
                WHERE p.deleted_at IS NULL AND p.step < ?
                  AND (c.id IS NULL OR (
                      c.deleted_at IS NULL AND COALESCE(c.status, 'active') != 'inactive'
                  ))
                """,
                (PIPELINE_MAX_STEP,),
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
