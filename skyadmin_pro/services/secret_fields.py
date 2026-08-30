"""Machine-bound encryption for sensitive fields stored in SQLite."""

from __future__ import annotations

import logging

from skyadmin_pro.services.crypto import _derive_fernet_key
from skyadmin_pro.services.license import get_machine_id

logger = logging.getLogger(__name__)

SECRET_PREFIX = "SKYSECRET1:"


class SecretDecryptError(ValueError):
    """Raised when an encrypted secret cannot be decrypted."""


def is_encrypted_secret(value: str | None) -> bool:
    """Return True when *value* uses the SkyAdmin encrypted-secret prefix."""
    return bool(value and value.startswith(SECRET_PREFIX))


def encrypt_secret(value: str) -> str:
    """Encrypt a short secret for storage. Empty input stays empty."""
    text = (value or "").strip()
    if not text:
        return ""
    if is_encrypted_secret(text):
        return text
    from cryptography.fernet import Fernet

    token = Fernet(_derive_fernet_key(get_machine_id())).encrypt(text.encode("utf-8"))
    return SECRET_PREFIX + token.decode("ascii")


def decrypt_secret(
    value: str | None,
    *,
    allow_legacy_plaintext: bool = False,
) -> str:
    """Decrypt a stored secret.

    By default this function is **fail-closed**:

    * Legacy plaintext values (no ``SKYSECRET1:`` prefix) return ``""``.
    * Corrupt or machine-mismatched ciphertext returns ``""``.

    Set ``allow_legacy_plaintext=True`` only in one-off migration code that
    must read rows before ``_migrate_secret_fields`` has run.
    """
    if not value:
        return ""
    if not is_encrypted_secret(value):
        if allow_legacy_plaintext:
            return value
        logger.warning("Refusing legacy plaintext secret (encrypt at rest required)")
        return ""

    from cryptography.fernet import Fernet, InvalidToken

    blob = value[len(SECRET_PREFIX) :]
    try:
        plain = Fernet(_derive_fernet_key(get_machine_id())).decrypt(blob.encode("ascii"))
        return plain.decode("utf-8")
    except InvalidToken:
        logger.warning("Encrypted secret could not be decrypted (wrong machine or tampered data)")
        return ""
    except (ValueError, OSError) as exc:
        logger.warning("Encrypted secret decode failed: %s", exc)
        return ""


def read_plaintext_for_migration(value: str | None) -> str:
    """Return plaintext for schema migration helpers only.

    Accepts either encrypted ``SKYSECRET1:`` values or legacy plaintext.
    Returns empty string when decryption fails.
    """
    if not value:
        return ""
    if is_encrypted_secret(value):
        return decrypt_secret(value)
    return str(value)
