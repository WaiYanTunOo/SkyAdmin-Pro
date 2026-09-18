"""Credential row transforms for Mobile Vault sync (Wave E)."""

from __future__ import annotations

from typing import Any

from skyadmin_pro.services.mobile_vault import (
    VAULT_SYNC_TABLES,
    is_mobile_vault_ciphertext,
    mobile_vault_configured,
    wrap_machine_secret_for_sync,
)
from skyadmin_pro.services.sync_schema import FK_CLIENT_COLUMN


def apply_vault_secret_for_push(db, table: str, payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Re-encrypt secret_value for cloud, or omit when passphrase unset.

    Returns (payload, passwords_included).
    """
    if table not in VAULT_SYNC_TABLES:
        return payload, False
    out = dict(payload)
    if not mobile_vault_configured(db):
        out.pop("secret_value", None)
        return out, False
    machine_ct = out.get("secret_value")
    wrapped = wrap_machine_secret_for_sync(db, machine_ct)
    if wrapped:
        out["secret_value"] = wrapped
        return out, True
    out.pop("secret_value", None)
    return out, True


def strip_mobile_secret_on_pull(table: str, row: dict[str, Any]) -> dict[str, Any]:
    """Never write vsk1 ciphertext (or plaintext) into local machine vault."""
    if table not in VAULT_SYNC_TABLES:
        return row
    out = dict(row)
    secret = out.get("secret_value")
    if secret is None:
        return out
    if is_mobile_vault_ciphertext(str(secret)) or not str(secret).startswith("SKYSECRET1:"):
        out.pop("secret_value", None)
    return out


def remap_credential_fks(table: str, payload: dict[str, Any], client_gid_map: dict[int, str | None]) -> dict[str, Any]:
    out = dict(payload)
    if table == "client_credentials":
        cid = out.get("client_id")
        gid = client_gid_map.get(int(cid)) if cid is not None else None
        out[FK_CLIENT_COLUMN] = gid
        out.pop("client_id", None)
    if table == "office_credentials":
        out.pop("contact_id", None)
    return out
