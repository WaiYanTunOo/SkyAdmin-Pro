from __future__ import annotations

from ..._const_6 import FK_CLIENT_COLUMN

PART_C = {
    "client_credentials": frozenset(
        {
            "credential_type",
            "registration_number",
            "login_id",
            "username",
            "secret_value",
            "portal_url",
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
    "office_credentials": frozenset(
        {
            "account_label",
            "login_id",
            "email",
            "secret_value",
            "system_type",
            "portal_url",
            "notes",
            "is_favorite",
            "global_id",
            "created_at",
            "updated_at",
            "deleted_at",
            "hlc",
        }
    ),
}
