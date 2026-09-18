from __future__ import annotations

from ..._const_6 import FK_CLIENT_COLUMN
from ..._const_7 import FK_GROUP_COLUMN

PART_A = {
    "client_groups": frozenset(
        {
            "name",
            "color",
            "global_id",
            "created_at",
            "updated_at",
            "deleted_at",
            "hlc",
        }
    ),
    "clients": frozenset(
        {
            "name",
            "company_name",
            "contact_name",
            "email",
            "status",
            "notes",
            "registration_number",
            "director",
            "contact_number",
            "registered_capital",
            "vat_registration",
            "business_address",
            "business_objectives",
            "tax_id",
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
            "global_id",
            "created_at",
            "updated_at",
            "deleted_at",
            "hlc",
            FK_GROUP_COLUMN,
        }
    ),
    "tasks": frozenset(
        {
            "title",
            "description",
            "status",
            "category",
            "due_date",
            "completed_at",
            "pipeline_item_id",
            "pipeline_step",
            "source_document_id",
            "global_id",
            "created_at",
            "updated_at",
            "deleted_at",
            "hlc",
            FK_CLIENT_COLUMN,
        }
    ),
}
