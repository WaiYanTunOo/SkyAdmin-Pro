from __future__ import annotations

from skyadmin_pro.services.mobile_vault import mobile_vault_configured


def vault_sync_status_note(db, vault_passwords: bool) -> str:
    if not mobile_vault_configured(db):
        return " Vault not synced — set passphrase in Settings."
    if vault_passwords:
        return " Vault passwords synced (ciphertext)."
    return ""
