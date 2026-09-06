"""Crypto backup/restore safety checks."""

import sqlite3
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


def test_restore_removes_sqlite_sidecars(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    db_file = tmp_path / "skyadmin_pro.db"
    db_file.write_bytes(b"live-db")
    (tmp_path / "skyadmin_pro.db-wal").write_bytes(b"stale-wal")
    (tmp_path / "skyadmin_pro.db-shm").write_bytes(b"stale-shm")
    archive = tmp_path / "roundtrip.skybackup"
    crypto.create_encrypted_backup(workspace, db_file, archive)

    target_db = tmp_path / "restored.db"
    (tmp_path / "restored.db-wal").write_bytes(b"old-wal")
    crypto.restore_encrypted_backup(archive, tmp_path / "restored_ws", target_db)
    assert target_db.read_bytes() == b"live-db"
    assert not (tmp_path / "restored.db-wal").exists()
    assert not (tmp_path / "restored.db-shm").exists()


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


def test_restore_rewrites_paths_for_cross_machine(tmp_path):
    """Paths from the old workspace root are rewritten to the new root."""
    old_ws = tmp_path / "old_machine" / "Workspace"
    old_ws.mkdir(parents=True)

    # Create a plain SQLite DB with app schema and absolute old-machine paths.
    db_file = tmp_path / "skyadmin_pro.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)",
        ("workspace_root", str(old_ws)),
    )
    conn.execute(
        "CREATE TABLE documents (id INTEGER PRIMARY KEY, client_id INTEGER, "
        "document_type TEXT, file_path TEXT)"
    )
    conn.execute(
        "INSERT INTO documents (client_id, document_type, file_path) VALUES (?, ?, ?)",
        (1, "tax", str(old_ws / "Clients" / "Acme" / "tax.pdf")),
    )
    conn.execute(
        "CREATE TABLE financial_documents (id INTEGER PRIMARY KEY, client_id INTEGER, "
        "category TEXT, file_name TEXT, file_path TEXT, stored_path TEXT)"
    )
    conn.execute(
        "INSERT INTO financial_documents (client_id, category, file_name, file_path, stored_path) "
        "VALUES (?, ?, ?, ?, ?)",
        (1, "invoice", "inv.pdf", str(old_ws / "Staging" / "inv.pdf"), str(old_ws / "Archive" / "inv.pdf")),
    )
    conn.commit()
    conn.close()

    # Create backup archive.
    archive = tmp_path / "cross_machine.skybackup"
    crypto.create_encrypted_backup(old_ws, db_file, archive)

    # Restore to a completely different workspace root.
    new_ws = tmp_path / "new_machine" / "Workspace"
    target_db = tmp_path / "restored.db"
    summary = crypto.restore_encrypted_backup(archive, new_ws, target_db)

    # Verify paths were rewritten.
    assert summary.paths_rewritten > 0
    conn2 = sqlite3.connect(str(target_db))
    try:
        # workspace_root setting updated.
        row = conn2.execute("SELECT value FROM settings WHERE key = 'workspace_root'").fetchone()
        assert row is not None
        assert row[0] == str(new_ws)

        # document file_path rewritten.
        row = conn2.execute("SELECT file_path FROM documents WHERE id = 1").fetchone()
        assert row is not None
        assert row[0].startswith(str(new_ws))
        assert "old_machine" not in row[0]

        # financial_documents paths rewritten.
        row = conn2.execute("SELECT file_path, stored_path FROM financial_documents WHERE id = 1").fetchone()
        assert row is not None
        assert row[0].startswith(str(new_ws))
        assert row[1].startswith(str(new_ws))
        assert "old_machine" not in row[0]
        assert "old_machine" not in row[1]
    finally:
        conn2.close()


def test_restore_no_path_rewrite_when_same_root(tmp_path):
    """No rewriting when the backup was created with the same workspace root."""
    ws = tmp_path / "workspace"
    ws.mkdir()

    db_file = tmp_path / "skyadmin_pro.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("workspace_root", str(ws)))
    conn.execute(
        "CREATE TABLE documents (id INTEGER PRIMARY KEY, client_id INTEGER, "
        "document_type TEXT, file_path TEXT)"
    )
    conn.execute("INSERT INTO documents (client_id, document_type, file_path) VALUES (?, ?, ?)", (1, "tax", str(ws / "a.pdf")))
    conn.commit()
    conn.close()

    archive = tmp_path / "same_root.skybackup"
    crypto.create_encrypted_backup(ws, db_file, archive)

    target_db = tmp_path / "restored.db"
    summary = crypto.restore_encrypted_backup(archive, ws, target_db)

    assert summary.paths_rewritten == 0
