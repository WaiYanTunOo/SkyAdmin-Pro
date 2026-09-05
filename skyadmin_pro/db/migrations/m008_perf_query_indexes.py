"""Migration 008 — composite/partial indexes for overdue and ongoing queries."""

from __future__ import annotations

from typing import TYPE_CHECKING

VERSION = 8
NAME = "perf_query_indexes"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin

_INDEXES = (
    """
    CREATE INDEX IF NOT EXISTS idx_documents_unpaid_overdue
    ON documents(payment_date, document_type, client_id)
    WHERE client_id IS NOT NULL
      AND COALESCE(paid, 0) = 0
      AND payment_date IS NOT NULL
      AND trim(payment_date) != ''
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_documents_ongoing_service
    ON documents(document_type, client_id)
    WHERE client_id IS NOT NULL
      AND progress = 'Ongoing'
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_supplier_payments_unpaid_due
    ON supplier_payments(due_date, supplier_id)
    WHERE paid = 0
      AND due_date IS NOT NULL
      AND trim(due_date) != ''
    """,
)


def upgrade(db: CoreMixin) -> None:
    with db.connection() as conn:
        for ddl in _INDEXES:
            conn.execute(ddl)
