from __future__ import annotations

from ..._const_6 import FK_CLIENT_COLUMN
from ..._const_11 import FK_SUPPLIER_COLUMN, FK_TASK_COLUMN

_SYNC_META = frozenset({"global_id", "created_at", "updated_at", "deleted_at", "hlc"})

PART_E = {
    "pipeline_items": frozenset({"service", "step", "step_date", "notes", FK_CLIENT_COLUMN} | _SYNC_META),
    "suppliers": frozenset({"name", "company_name", "contact", "notes"} | _SYNC_META),
    "supplier_payments": frozenset(
        {
            "amount",
            "due_date",
            "paid",
            "paid_date",
            "notes",
            FK_CLIENT_COLUMN,
            FK_SUPPLIER_COLUMN,
        }
        | _SYNC_META
    ),
    "supplier_services": frozenset(
        {
            "company_name",
            "service_type",
            "expiry_date",
            "notes",
            FK_SUPPLIER_COLUMN,
        }
        | _SYNC_META
    ),
    "courier_logs": frozenset(
        {
            "tracking_number",
            "driver_name",
            "date_sent",
            "destination",
            "notes",
            FK_CLIENT_COLUMN,
            FK_TASK_COLUMN,
        }
        | _SYNC_META
    ),
    "client_months": frozenset({"month_key", "status", "note", FK_CLIENT_COLUMN} | _SYNC_META),
    "renewal_items": frozenset(
        {
            "template_name",
            "item",
            "due_days",
            "done",
            "done_at",
            FK_CLIENT_COLUMN,
        }
        | _SYNC_META
    ),
    "tax_cycle_log": frozenset({"field", "old_value", "new_value", "changed_at", FK_CLIENT_COLUMN} | _SYNC_META),
    "recurring_tasks": frozenset(
        {
            "title_template",
            "category",
            "frequency",
            "day_of_month",
            "last_generated",
            FK_CLIENT_COLUMN,
        }
        | _SYNC_META
    ),
}
