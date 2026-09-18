"""Mobile Vault constants — passphrase-gated sync ciphertext (never machine-bound)."""

from __future__ import annotations

MOBILE_VAULT_PREFIX = "vsk1:"
PBKDF2_ITERATIONS = 210_000
SALT_LEN = 16
NONCE_LEN = 12
KEY_LEN = 32

SETTING_MOBILE_VAULT_SALT = "mobile_vault_salt"
SETTING_MOBILE_VAULT_VERIFIER = "mobile_vault_verifier"
SETTING_MOBILE_VAULT_KEY = "mobile_vault_key_blob"

VAULT_SYNC_TABLES: frozenset[str] = frozenset(
    {
        "client_credentials",
        "office_credentials",
    }
)
