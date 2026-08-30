"""Crypto backup/restore safety checks."""

import zipfile

import pytest
from cryptography.fernet import Fernet

from skyadmin_pro.services import crypto


def test_inspect_encrypted_backup_reports_contents(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    note = workspace / "Clients" / "Acme"
    note.mkdir(parents=True)
    note.joinpath("readme.txt").write_text("hello", encoding="utf-8")
    db_file = tmp_path / "skyadmin_pro.db"
    db_file.write_bytes(b"db-bytes")

    archive = tmp_path / "good.skybackup"
    crypto.create_encrypted_backup(workspace, db_file, archive)
    info = crypto.inspect_encrypted_backup(archive)
    assert info.has_database is True
    assert info.database_bytes == len(b"db-bytes")
    assert info.workspace_file_count == 1
    assert info.workspace_bytes == len(b"hello")
    assert info.encrypted_bytes == archive.stat().st_size


def test_restore_returns_summary(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    db_file = tmp_path / "skyadmin_pro.db"
    db_file.write_bytes(b"live-db")
    archive = tmp_path / "roundtrip.skybackup"
    crypto.create_encrypted_backup(workspace, db_file, archive)

    target_ws = tmp_path / "restored_ws"
    target_db = tmp_path / "restored.db"
    summary = crypto.restore_encrypted_backup(archive, target_ws, target_db)
    assert target_db.read_bytes() == b"live-db"
    assert summary.database_bytes == len(b"live-db")
    assert summary.workspace_files_restored == 0


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


def test_restore_rejects_zip_slip_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    db_file = tmp_path / "skyadmin_pro.db"
    db_file.write_bytes(b"live-db")

    archive = tmp_path / "evil.skybackup"
    zip_path = tmp_path / "inner.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("skyadmin_pro.db", b"replacement-db")
        zf.writestr("Workspace/../../outside.txt", b"pwned")

    token = Fernet(crypto._derive_backup_key()).encrypt(zip_path.read_bytes())
    archive.write_bytes(crypto.MAGIC + token)

    with pytest.raises(ValueError, match="escapes destination"):
        crypto.restore_encrypted_backup(archive, workspace, db_file)

    assert db_file.read_bytes() == b"live-db"
    assert not (tmp_path / "outside.txt").exists()
