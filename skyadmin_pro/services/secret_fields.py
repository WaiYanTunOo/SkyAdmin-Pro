"""Machine-bound encryption for sensitive fields stored in SQLite."""

from __future__ import annotations

from skyadmin_pro.services.crypto import _derive_fernet_key
from skyadmin_pro.services.license import get_machine_id

SECRET_PREFIX = "SKYSECRET1:"


def is_encrypted_secret(value: str | None) -> bool:
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


def decrypt_secret(value: str | None) -> str:
    """Decrypt a stored secret. Legacy plaintext values pass through."""
    if not value:
        return ""
    if not is_encrypted_secret(value):
        return value
    from cryptography.fernet import Fernet, InvalidToken

    blob = value[len(SECRET_PREFIX) :]
    try:
        plain = Fernet(_derive_fernet_key(get_machine_id())).decrypt(blob.encode("ascii"))
        return plain.decode("utf-8")
    except (InvalidToken, ValueError, OSError):
        return ""
