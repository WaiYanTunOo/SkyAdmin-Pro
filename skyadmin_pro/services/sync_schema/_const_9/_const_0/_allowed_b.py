from __future__ import annotations

from ..._const_6 import FK_CLIENT_COLUMN

PART_B = {
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
