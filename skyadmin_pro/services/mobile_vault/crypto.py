"""Passphrase-derived AES-GCM helpers for mobile vault sync ciphertext."""

from __future__ import annotations

import base64
import hashlib
import secrets

from ._const import (
    KEY_LEN,
    MOBILE_VAULT_PREFIX,
    NONCE_LEN,
    PBKDF2_ITERATIONS,
    SALT_LEN,
)


def is_mobile_vault_ciphertext(value: str | None) -> bool:
    return bool(value and str(value).startswith(MOBILE_VAULT_PREFIX))


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def derive_key(passphrase: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        (passphrase or "").encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=KEY_LEN,
    )


def verifier_for_key(key: bytes) -> str:
    return hashlib.sha256(key).hexdigest()


def encrypt_with_key(plaintext: str, key: bytes, salt: bytes) -> str:
    """Encrypt *plaintext* with a derived vault key. Empty input stays empty."""
    text = (plaintext or "").strip()
    if not text:
        return ""
    if is_mobile_vault_ciphertext(text):
        return text
    if len(salt) != SALT_LEN or len(key) != KEY_LEN:
        raise ValueError("mobile vault key/salt length mismatch")
    nonce = secrets.token_bytes(NONCE_LEN)
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    ct = AESGCM(key).encrypt(nonce, text.encode("utf-8"), None)
    return MOBILE_VAULT_PREFIX + _b64e(salt + nonce + ct)


def encrypt_with_passphrase(plaintext: str, passphrase: str, *, salt: bytes | None = None) -> str:
    salt_b = salt if salt is not None else secrets.token_bytes(SALT_LEN)
    return encrypt_with_key(plaintext, derive_key(passphrase, salt_b), salt_b)


def decrypt_with_key(value: str | None, key: bytes) -> str:
    if not value or not is_mobile_vault_ciphertext(value):
        return ""
    try:
        raw = _b64d(value[len(MOBILE_VAULT_PREFIX) :])
        if len(raw) < SALT_LEN + NONCE_LEN + 16:
            return ""
        nonce = raw[SALT_LEN : SALT_LEN + NONCE_LEN]
        ct = raw[SALT_LEN + NONCE_LEN :]
        from cryptography.exceptions import InvalidTag
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        return AESGCM(key).decrypt(nonce, ct, None).decode("utf-8")
    except (ValueError, OSError, InvalidTag):
        return ""


def decrypt_with_passphrase(value: str | None, passphrase: str) -> str:
    """Decrypt a ``vsk1:`` blob. Wrong passphrase or corrupt data returns \"\"."""
    if not value or not is_mobile_vault_ciphertext(value):
        return ""
    try:
        raw = _b64d(value[len(MOBILE_VAULT_PREFIX) :])
        if len(raw) < SALT_LEN + NONCE_LEN + 16:
            return ""
        salt_b = raw[:SALT_LEN]
        return decrypt_with_key(value, derive_key(passphrase, salt_b))
    except (ValueError, OSError):
        return ""


def new_salt() -> bytes:
    return secrets.token_bytes(SALT_LEN)
