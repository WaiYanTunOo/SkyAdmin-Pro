"""Desktop sync table manifest — keep aligned with skyadmin-worker/src/sync_schema.ts."""

from __future__ import annotations

SYNC_SCHEMA_VERSION = 3

# Parent groups first so clients can remap group_global_id on apply.
SYNC_TABLES: tuple[str, ...] = (
    "client_groups",
    "clients",
    "tasks",
    "office_contacts",
    "notebook_entries",
)
SYNC_PUSH_ORDER: tuple[str, ...] = SYNC_TABLES
SYNC_PULL_PAGE_SIZE = 500
SYNC_PULL_MAX_PAGES = 100
# Global push batch cap (across all tables) — keeps Worker request bodies bounded.
SYNC_PUSH_PAGE_SIZE = 200

FK_CLIENT_COLUMN = "client_global_id"
FK_GROUP_COLUMN = "group_global_id"

# Numeric clients.group_id stays local; membership syncs as group_global_id.
SYNC_EXCLUDED_COLUMNS: dict[str, frozenset[str]] = {
    "client_groups": frozenset({"id"}),
    "clients": frozenset({"ird_password", "id", "group_id"}),
    "tasks": frozenset({"id"}),
    "office_contacts": frozenset({"id"}),
    "notebook_entries": frozenset({"id"}),
}

SYNC_ALLOWED_COLUMNS: dict[str, frozenset[str]] = {
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
    "office_contacts": frozenset(
        {
            "name",
            "role_title",
            "organization",
            "department",
            "phone",
            "email",
            "line_id",
            "category",
            "notes",
            "is_favorite",
            "global_id",
            "created_at",
            "updated_at",
            "deleted_at",
            "hlc",
            FK_CLIENT_COLUMN,
        }
    ),
    "notebook_entries": frozenset(
        {
            "entry_type",
            "title",
            "body",
            "entry_date",
            "author",
            "follow_up_date",
            "is_pinned",
            "global_id",
            "created_at",
            "updated_at",
            "deleted_at",
            "hlc",
            FK_CLIENT_COLUMN,
        }
    ),
}

__all__ = [
    "FK_CLIENT_COLUMN",
    "FK_GROUP_COLUMN",
    "SYNC_ALLOWED_COLUMNS",
    "SYNC_EXCLUDED_COLUMNS",
    "SYNC_PULL_MAX_PAGES",
    "SYNC_PULL_PAGE_SIZE",
    "SYNC_PUSH_ORDER",
    "SYNC_SCHEMA_VERSION",
    "SYNC_TABLES",
]
