"""Vault encrypt/decrypt round-trip tests."""

from __future__ import annotations

from skyadmin_pro.services.vault import decrypt_vault_secret, encrypt_vault_secret


def test_vault_encrypt_decrypt_roundtrip(monkeypatch):
    monkeypatch.setattr("skyadmin_pro.services.secret_fields.get_machine_id", lambda: "ABCD1234EFGH5678")
    plain = "s3cret-P@ss"
    stored = encrypt_vault_secret(plain)
    assert stored.startswith("SKYSECRET1:")
    assert decrypt_vault_secret(stored) == plain


def test_vault_empty_stays_empty(monkeypatch):
    monkeypatch.setattr("skyadmin_pro.services.secret_fields.get_machine_id", lambda: "ABCD1234EFGH5678")
    assert encrypt_vault_secret("") == ""
    assert decrypt_vault_secret("") == ""
