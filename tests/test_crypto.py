"""Crypto backup/restore safety checks."""

import zipfile

import pytest
from cryptography.fernet import Fernet

from skyadmin_pro.services import crypto


def test_restore_rejects_archive_without_database(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    db_file = tmp_path / "skyadmin_pro.db"
    db_file.write_bytes(b"live-db")

    archive = tmp_path / "bad.skybackup"
    zip_path = tmp_path / "inner.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("Workspace/note.txt", "only workspace data")

    token = Fernet(crypto._derive_backup_key()).encrypt(zip_path.read_bytes())
    archive.write_bytes(crypto.MAGIC + token)

    with pytest.raises(ValueError, match="missing skyadmin_pro.db"):
        crypto.restore_encrypted_backup(archive, workspace, db_file)

    assert db_file.read_bytes() == b"live-db"


def test_encrypt_file_round_trip(tmp_path):
    target = tmp_path / "secret.txt"
    target.write_text("plain", encoding="utf-8")
    mid = "TESTMACHINE00001"
    assert crypto.encrypt_file(target, mid) is True
    assert crypto.is_encrypted(target)
    assert crypto.decrypt_file(target, mid) is True
    assert target.read_text(encoding="utf-8") == "plain"
