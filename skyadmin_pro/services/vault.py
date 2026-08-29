"""Password vault helpers — machine-bound secret storage."""

from __future__ import annotations

from skyadmin_pro.services.secret_fields import decrypt_secret, encrypt_secret


def encrypt_vault_secret(value: str) -> str:
    return encrypt_secret(value or "")


def decrypt_vault_secret(value: str | None) -> str:
    return decrypt_secret(value)


def _attach_password(data: dict) -> dict:
    stored = data.pop("secret_value", "")
    data["password"] = decrypt_vault_secret(stored)
    data["secret_value"] = data["password"]
    return data


def prepare_vault_row(row: dict | None) -> dict | None:
    """Legacy alias — prefer prepare_client_credential_row / prepare_office_credential_row."""
    if row is None:
        return None
    return _attach_password(dict(row))


def prepare_client_credential_row(row: dict | None) -> dict | None:
    if row is None:
        return None
    return _attach_password(dict(row))


def prepare_office_credential_row(row: dict | None) -> dict | None:
    if row is None:
        return None
    return _attach_password(dict(row))
