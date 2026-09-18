"""Mobile Vault encrypt/decrypt and sync ciphertext tests (Wave E)."""

from __future__ import annotations

from skyadmin_pro.database import Database
from skyadmin_pro.services.data_sync import collect_local_changes, ensure_sync_ids
from skyadmin_pro.services.mobile_vault import (
    MOBILE_VAULT_PREFIX,
    decrypt_with_passphrase,
    encrypt_with_passphrase,
    mobile_vault_configured,
    set_mobile_vault_passphrase,
    wrap_machine_secret_for_sync,
)
from skyadmin_pro.services.secret_fields import encrypt_secret


def test_mobile_vault_encrypt_decrypt_roundtrip():
    plain = "portal-s3cret!"
    ct = encrypt_with_passphrase(plain, "passphrase-ok")
    assert ct.startswith(MOBILE_VAULT_PREFIX)
    assert plain not in ct
    assert decrypt_with_passphrase(ct, "passphrase-ok") == plain
    assert decrypt_with_passphrase(ct, "wrong-pass") == ""


def test_sync_without_passphrase_omits_secret(tmp_path, fake_app_dir, monkeypatch):
    monkeypatch.setattr(
        "skyadmin_pro.services.secret_fields.get_machine_id",
        lambda: "TESTMACHINE00001",
    )
    db = Database(tmp_path / "vault_sync.db")
    client_id = db.get_or_create_client("Portal Co")
    db.add_client_credential(
        client_id=client_id,
        credential_type="RD",
        login_id="rd-user",
        password="plain-should-not-sync",
    )
    ensure_sync_ids(db)
    assert not mobile_vault_configured(db)
    changes = collect_local_changes(db)
    creds = [c for c in changes if c["table"] == "client_credentials"]
    assert creds
    row = creds[0]["row"]
    assert "secret_value" not in row
    assert "plain-should-not-sync" not in str(row)


def test_sync_with_passphrase_pushes_ciphertext_only(tmp_path, fake_app_dir, monkeypatch):
    monkeypatch.setattr(
        "skyadmin_pro.services.secret_fields.get_machine_id",
        lambda: "TESTMACHINE00001",
    )
    db = Database(tmp_path / "vault_sync2.db")
    ok, _ = set_mobile_vault_passphrase(db, "desktop-pass")
    assert ok
    client_id = db.get_or_create_client("Portal Co 2")
    db.add_client_credential(
        client_id=client_id,
        credential_type="DBD",
        login_id="dbd-user",
        password="sync-me-secret",
    )
    ensure_sync_ids(db)
    changes = collect_local_changes(db)
    creds = [c for c in changes if c["table"] == "client_credentials"]
    assert creds
    secret = creds[0]["row"].get("secret_value") or ""
    assert secret.startswith(MOBILE_VAULT_PREFIX)
    assert "sync-me-secret" not in secret
    assert decrypt_with_passphrase(secret, "desktop-pass") == "sync-me-secret"


def test_wrap_machine_secret_uses_local_key(tmp_path, fake_app_dir, monkeypatch):
    monkeypatch.setattr(
        "skyadmin_pro.services.secret_fields.get_machine_id",
        lambda: "TESTMACHINE00001",
    )
    db = Database(tmp_path / "vault_wrap.db")
    set_mobile_vault_passphrase(db, "wrap-pass-99")
    machine = encrypt_secret("office-pw")
    wrapped = wrap_machine_secret_for_sync(db, machine)
    assert wrapped.startswith(MOBILE_VAULT_PREFIX)
    assert decrypt_with_passphrase(wrapped, "wrap-pass-99") == "office-pw"


def test_pull_strips_mobile_ciphertext():
    from skyadmin_pro.services.data_sync.cred_payload import strip_mobile_secret_on_pull

    row = strip_mobile_secret_on_pull(
        "client_credentials",
        {"login_id": "u", "secret_value": MOBILE_VAULT_PREFIX + "abc"},
    )
    assert "secret_value" not in row
    assert row["login_id"] == "u"
