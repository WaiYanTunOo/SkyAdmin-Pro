from __future__ import annotations

SYNC_EXCLUDED_COLUMNS: dict[str, frozenset[str]] = {
    "client_groups": frozenset({"id"}),
    "clients": frozenset({"ird_password", "id", "group_id"}),
    "tasks": frozenset({"id"}),
    "office_contacts": frozenset({"id"}),
    "notebook_entries": frozenset({"id"}),
    "client_credentials": frozenset({"id", "client_id"}),
    "office_credentials": frozenset({"id", "contact_id"}),
    "documents": frozenset({"id", "client_id"}),
    "financial_documents": frozenset({"id", "client_id"}),
    "pipeline_items": frozenset({"id", "client_id"}),
    "suppliers": frozenset({"id"}),
    "supplier_payments": frozenset({"id", "client_id", "supplier_id"}),
    "supplier_services": frozenset({"id", "supplier_id"}),
    "courier_logs": frozenset({"id", "client_id", "task_id"}),
    "client_months": frozenset({"id", "client_id"}),
    "renewal_items": frozenset({"id", "client_id"}),
    "tax_cycle_log": frozenset({"id", "client_id"}),
    "recurring_tasks": frozenset({"id", "client_id"}),
}
