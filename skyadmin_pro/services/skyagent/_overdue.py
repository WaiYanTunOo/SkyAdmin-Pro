"""Overdue-document query aligned with dashboard list_overdue_services."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from skyadmin_pro.db.sql_helpers import _in_clause

FetchAll = Callable[[str, tuple], list[dict]]


def query_overdue_documents(db: Any, fetch_all: FetchAll) -> list[dict]:
    """Unpaid docs past payment_date, limited to configured service types."""
    list_fn = getattr(db, "list_service_types", None)
    types = tuple(list_fn()) if callable(list_fn) else ()
    if not types:
        return []
    clause, params = _in_clause("d.document_type", types)
    sql = f"""
        SELECT d.id, d.document_type, d.payment_date, d.amount, c.name AS client_name
        FROM documents d
        LEFT JOIN clients c ON c.id = d.client_id
        WHERE d.deleted_at IS NULL AND d.client_id IS NOT NULL
          AND c.deleted_at IS NULL AND COALESCE(c.status, 'active') != 'inactive'
          AND d.payment_date IS NOT NULL AND trim(d.payment_date) != ''
          AND date(d.payment_date) < date('now', 'localtime')
          AND COALESCE(d.paid, 0) = 0
          AND {clause}
        ORDER BY d.payment_date ASC
    """
    return fetch_all(sql, tuple(params))
