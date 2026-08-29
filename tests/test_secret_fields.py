"""IRD password encryption at rest."""

import sqlite3

import pytest

from skyadmin_pro.database import Database
from skyadmin_pro.services.secret_fields import (
    decrypt_secret,
    encrypt_secret,
    is_encrypted_secret,
)


def test_secret_round_trip(fake_app_dir, monkeypatch):
    monkeypatch.setattr(
        "skyadmin_pro.services.secret_fields.get_machine_id",
        lambda: "TESTMACHINE00001",
    )
    plain = "ird-portal-secret"
    stored = encrypt_secret(plain)
    assert is_encrypted_secret(stored)
    assert decrypt_secret(stored) == plain
    assert decrypt_secret(plain) == plain  # legacy plaintext passthrough


def test_database_encrypts_and_decrypts_ird_password(tmp_path, fake_app_dir, monkeypatch):
    monkeypatch.setattr(
        "skyadmin_pro.services.secret_fields.get_machine_id",
        lambda: "TESTMACHINE00001",
    )
    db = Database(tmp_path / "test.db")
    client_id = db.get_or_create_client("Acme Co")
    db.update_client_fields(client_id, ird_password="portal-pass-123")

    with sqlite3.connect(db.db_file) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT ird_password FROM clients WHERE id = ?", (client_id,)
        ).fetchone()
    stored = row["ird_password"]
    assert is_encrypted_secret(stored)
    assert "portal-pass-123" not in stored

    loaded = db.get_client(client_id)
    assert loaded is not None
    assert loaded["ird_password"] == "portal-pass-123"
    assert loaded["tax_id"] is None or isinstance(loaded["tax_id"], str)


def test_plaintext_ird_password_migrated_on_startup(tmp_path, fake_app_dir, monkeypatch):
    monkeypatch.setattr(
        "skyadmin_pro.services.secret_fields.get_machine_id",
        lambda: "TESTMACHINE00001",
    )
    db = Database(tmp_path / "legacy.db")
    client_id = db.get_or_create_client("Legacy Ltd")
    with sqlite3.connect(db.db_file) as conn:
        conn.execute(
            "UPDATE clients SET ird_password = ? WHERE id = ?",
            ("plain-old-pass", client_id),
        )
        conn.commit()

    db._migrate_secret_fields()
    client = db.get_client(client_id)
    assert client is not None
    assert client["ird_password"] == "plain-old-pass"

    with sqlite3.connect(db.db_file) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT ird_password FROM clients WHERE id = ?", (client_id,)
        ).fetchone()
    assert is_encrypted_secret(row["ird_password"])
