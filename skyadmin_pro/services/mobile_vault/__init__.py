"""Mobile Vault — passphrase-gated credential ciphertext for /viewer sync."""

from __future__ import annotations

from ._const import (
    MOBILE_VAULT_PREFIX,
    SETTING_MOBILE_VAULT_KEY,
    SETTING_MOBILE_VAULT_SALT,
    SETTING_MOBILE_VAULT_VERIFIER,
    VAULT_SYNC_TABLES,
)
from .crypto import (
    decrypt_with_passphrase,
    encrypt_with_key,
    encrypt_with_passphrase,
    is_mobile_vault_ciphertext,
)
from .settings import (
    clear_mobile_vault,
    load_vault_key,
    load_vault_salt,
    mobile_vault_configured,
    set_mobile_vault_passphrase,
    verify_mobile_vault_passphrase,
)

__all__ = [
    "MOBILE_VAULT_PREFIX",
    "SETTING_MOBILE_VAULT_KEY",
    "SETTING_MOBILE_VAULT_SALT",
    "SETTING_MOBILE_VAULT_VERIFIER",
    "VAULT_SYNC_TABLES",
    "clear_mobile_vault",
    "decrypt_with_passphrase",
    "encrypt_with_key",
    "encrypt_with_passphrase",
    "is_mobile_vault_ciphertext",
    "load_vault_key",
    "load_vault_salt",
    "mobile_vault_configured",
    "set_mobile_vault_passphrase",
    "verify_mobile_vault_passphrase",
    "wrap_machine_secret_for_sync",
]


def wrap_machine_secret_for_sync(db, machine_ciphertext: str | None) -> str:
    """Decrypt machine-bound secret and re-encrypt with mobile vault key."""
    from skyadmin_pro.services.secret_fields import decrypt_secret

    key = load_vault_key(db)
    salt = load_vault_salt(db)
    if key is None or salt is None:
        return ""
    plain = decrypt_secret(machine_ciphertext)
    if not plain:
        return ""
    return encrypt_with_key(plain, key, salt)
