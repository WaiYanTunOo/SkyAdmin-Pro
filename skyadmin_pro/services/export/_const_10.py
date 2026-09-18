from __future__ import annotations

FORBIDDEN_EXPORT_COLUMNS = frozenset(
    {
        "ird_password",
        "secret_value",
        "password",
        "vault",
        "login_id",
        "registration_number",
    }
)
