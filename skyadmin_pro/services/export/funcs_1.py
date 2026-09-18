from __future__ import annotations

from typing import Any

from ..importer.funcs import Database
from .funcs_0 import _plain_rows


def collect_export_payload(
    db: Database,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    client_ids: list[int] | None = None,
    visible_only: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Gather export sheet data as plain dicts (safe to pickle across processes).

    NOTE (S2): SQL-side filtering/pagination deliberately deferred here. The
    filters below are case-insensitive (status), relational across tables
    (client_ids resolved via client_name joins), and applied to heterogeneous
    date-string columns, while the underlying list_* methods only expose
    per-table exact-match filters — pushing down would change export
    semantics. Pagination would not lower peak memory either (the workbook
    itself holds every row). Revisit only with per-method filter support plus
    a semantics audit.
    """

    tasks = _plain_rows(db.list_tasks())
    clients = _plain_rows(db.list_clients())
    documents = _plain_rows(db.list_documents())
    courier = _plain_rows(db.list_courier_logs())
    suppliers = _plain_rows(db.list_suppliers())
    supplier_payments = _plain_rows(db.list_supplier_payments())
    supplier_services = _plain_rows(db.list_all_supplier_services())
    pipeline = _plain_rows(db.list_pipeline_items())
    renewals = _plain_rows(db.all_service_renewals())
    financial_docs = _plain_rows(db.all_financial_documents())

    if client_ids:
        id_set = set(client_ids)
        clients = [c for c in clients if c.get("id") in id_set]
        client_name_set = {c.get("name", "") for c in clients}
        documents = [d for d in documents if d.get("client_name") in client_name_set]
        tasks = [t for t in tasks if t.get("client_name") in client_name_set]

    if status:
        s = status.strip().lower()
        tasks = [t for t in tasks if (t.get("status") or "").lower() == s]
        clients = [c for c in clients if (c.get("status") or "").lower() == s]

    if date_from:
        tasks = [t for t in tasks if (t.get("created_at") or "") >= date_from]
        documents = [d for d in documents if (d.get("expiry_date") or "") >= date_from]
    if date_to:
        tasks = [t for t in tasks if (t.get("created_at") or "") <= date_to]
        documents = [d for d in documents if (d.get("expiry_date") or "") <= date_to]

    return {
        "tasks": tasks,
        "clients": clients,
        "documents": documents,
        "courier": courier,
        "suppliers": suppliers,
        "supplier_payments": supplier_payments,
        "supplier_services": supplier_services,
        "pipeline": pipeline,
        "renewals": renewals,
        "financial_docs": financial_docs,
        "visible_only": visible_only,
    }
