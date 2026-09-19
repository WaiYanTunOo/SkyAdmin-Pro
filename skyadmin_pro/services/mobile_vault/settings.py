"""Local settings for Mobile Vault passphrase verifier (never sync passphrase)."""

from __future__ import annotations

from typing import Any

from ._const import (
    SETTING_MOBILE_VAULT_KEY,
    SETTING_MOBILE_VAULT_SALT,
    SETTING_MOBILE_VAULT_VERIFIER,
)
from .crypto import derive_key, new_salt, verifier_for_key


def mobile_vault_configured(db: Any) -> bool:
    salt = (db.get_setting(SETTING_MOBILE_VAULT_SALT) or "").strip()
    ver = (db.get_setting(SETTING_MOBILE_VAULT_VERIFIER) or "").strip()
    key = (db.get_setting(SETTING_MOBILE_VAULT_KEY) or "").strip()
    return bool(salt and ver and key)


def clear_mobile_vault(db: Any) -> None:
    db.set_setting(SETTING_MOBILE_VAULT_SALT, "")
    db.set_setting(SETTING_MOBILE_VAULT_VERIFIER, "")
    db.set_setting(SETTING_MOBILE_VAULT_KEY, "")


def set_mobile_vault_passphrase(db: Any, passphrase: str) -> tuple[bool, str]:
    """Store salt+verifier+machine-bound key. Passphrase is never persisted."""
    text = (passphrase or "").strip()
    if len(text) < 8:
        return False, "Passphrase must be at least 8 characters."
    from skyadmin_pro.services.secret_fields import encrypt_secret

    salt = new_salt()
    key = derive_key(text, salt)
    db.set_setting(SETTING_MOBILE_VAULT_SALT, salt.hex())
    db.set_setting(SETTING_MOBILE_VAULT_VERIFIER, verifier_for_key(key))
    db.set_setting(SETTING_MOBILE_VAULT_KEY, encrypt_secret(key.hex()))
    _touch_credential_rows(db)
    return True, (
        "Mobile Vault passphrase saved locally. Sync Now to push ciphertext. "
        "Changing the passphrase re-encrypts on the next sync."
    )


def verify_mobile_vault_passphrase(db: Any, passphrase: str) -> bool:
    salt_hex = (db.get_setting(SETTING_MOBILE_VAULT_SALT) or "").strip()
    expected = (db.get_setting(SETTING_MOBILE_VAULT_VERIFIER) or "").strip()
    if not salt_hex or not expected:
        return False
    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    return verifier_for_key(derive_key(passphrase, salt)) == expected


def load_vault_salt(db: Any) -> bytes | None:
    salt_hex = (db.get_setting(SETTING_MOBILE_VAULT_SALT) or "").strip()
    if not salt_hex:
        return None
    try:
        return bytes.fromhex(salt_hex)
    except ValueError:
        return None


def load_vault_key(db: Any) -> bytes | None:
    """Load the machine-bound AES key used to wrap secrets on Sync Now."""
    from skyadmin_pro.services.secret_fields import decrypt_secret, is_encrypted_secret

    blob = (db.get_setting(SETTING_MOBILE_VAULT_KEY) or "").strip()
    if not blob or not is_encrypted_secret(blob):
        return None
    hex_key = decrypt_secret(blob)
    if not hex_key:
        return None
    try:
        key = bytes.fromhex(hex_key)
    except ValueError:
        return None
    return key if len(key) == 32 else None


def _touch_credential_rows(db: Any) -> None:
    """Bump updated_at so next sync re-pushes ciphertext under the new key."""
    try:
        now = db._now()
        with db.connection() as conn:
            for table in ("client_credentials", "office_credentials"):
                cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
                if "updated_at" in cols:
                    conn.execute(f"UPDATE {table} SET updated_at = ?", (now,))
    except Exception as e:
        import logging

        logging.error(f"UI Error: {e}")
