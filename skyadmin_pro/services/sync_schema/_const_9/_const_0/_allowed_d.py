from __future__ import annotations

from ..._const_6 import FK_CLIENT_COLUMN

_DRIVE_META = frozenset(
    {
        "drive_file_id",
        "drive_parent_path",
        "content_hash",
        "byte_size",
        "mime_type",
        "original_filename",
    }
)

PART_D = {
    "documents": frozenset(
        {
            "document_type",
            "expiry_date",
            "amount",
            "payment_date",
            "start_date",
            "progress",
            "paid",
            "file_name",
            "file_path",
            "completed_at",
            "global_id",
            "created_at",
            "updated_at",
            "deleted_at",
            "hlc",
            FK_CLIENT_COLUMN,
        }
    )
    | _DRIVE_META,
    "financial_documents": frozenset(
        {
            "category",
            "subcategory",
            "file_name",
            "file_path",
            "stored_path",
            "amount",
            "doc_date",
            "description",
            "global_id",
            "created_at",
            "updated_at",
            "deleted_at",
            "hlc",
            FK_CLIENT_COLUMN,
        }
    )
    | _DRIVE_META,
}
