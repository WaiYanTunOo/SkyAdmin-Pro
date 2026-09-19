from __future__ import annotations

FK_SUPPLIER_COLUMN = "supplier_global_id"
FK_TASK_COLUMN = "task_global_id"

# Tables that remap numeric client_id ↔ client_global_id on push/pull.
CLIENT_FK_TABLES: frozenset[str] = frozenset(
    {
        "tasks",
        "office_contacts",
        "notebook_entries",
        "client_credentials",
        "documents",
        "financial_documents",
        "pipeline_items",
        "supplier_payments",
        "courier_logs",
        "client_months",
        "renewal_items",
        "tax_cycle_log",
        "recurring_tasks",
    }
)

# Tables that remap numeric supplier_id ↔ supplier_global_id.
SUPPLIER_FK_TABLES: frozenset[str] = frozenset(
    {
        "supplier_payments",
        "supplier_services",
    }
)

# Tables that remap numeric task_id ↔ task_global_id.
TASK_FK_TABLES: frozenset[str] = frozenset({"courier_logs"})
