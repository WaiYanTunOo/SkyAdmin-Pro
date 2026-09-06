"""Vault encrypt/decrypt round-trip tests."""

from __future__ import annotations

from skyadmin_pro.database import Database
from skyadmin_pro.db.cipher import CipherRow
from skyadmin_pro.db.cipher import connect as cipher_connect
from skyadmin_pro.services.secret_fields import is_encrypted_secret
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


def test_vault_write_stores_ciphertext_and_decrypts(tmp_path, fake_app_dir, monkeypatch):
    """add_client_credential → DB holds SKYSECRET1 ciphertext → read path decrypts."""
    monkeypatch.setattr(
        "skyadmin_pro.services.secret_fields.get_machine_id",
        lambda: "TESTMACHINE00001",
    )
    db = Database(tmp_path / "vault.db")
    client_id = db.get_or_create_client("Vault Co")
    entry_id = db.add_client_credential(
        client_id=client_id,
        credential_type="DBD",
        login_id="portal-user",
        password="vault-plain-secret",
    )

    with cipher_connect(db.db_file) as conn:
        conn.row_factory = CipherRow
        row = conn.execute(
            "SELECT secret_value FROM client_credentials WHERE id = ?",
            (entry_id,),
        ).fetchone()
    stored = row["secret_value"]
    assert stored.startswith("SKYSECRET1:")
    assert is_encrypted_secret(stored)
    assert "vault-plain-secret" not in stored

    loaded = db.get_client_credential(entry_id)
    assert loaded is not None
    assert loaded["password"] == "vault-plain-secret"
    assert decrypt_vault_secret(stored) == "vault-plain-secret"
