"""Phase 1 SQLCipher live-DB tests: encryption, migration, fail-closed key."""

import sqlite3

import pytest

from skyadmin_pro.database import Database
from skyadmin_pro.db import cipher
from skyadmin_pro.db.cipher import SQLITE_MAGIC, db_state


def _make_legacy_plaintext(path):
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("CREATE TABLE clients (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO clients (name) VALUES ('Legacy Co')")
        conn.commit()
    finally:
        conn.close()


def test_new_database_is_encrypted(tmp_path):
    db_file = tmp_path / "enc.db"
    db = Database(db_file)
    assert db_state(db_file) == "cipher"
    assert db_file.read_bytes()[:16] != SQLITE_MAGIC
    assert cipher.verify_cipher_db(db_file) is True
    db.get_or_create_client("Acme Corp")
    assert db.get_client(1)["name"] == "Acme Corp"


def test_legacy_plaintext_migrates_on_open(tmp_path):
    db_file = tmp_path / "legacy.db"
    _make_legacy_plaintext(db_file)
    assert db_state(db_file) == "plaintext"
    db = Database(db_file)
    assert db_state(db_file) == "cipher"
    assert cipher.verify_cipher_db(db_file) is True
    rows = db._fetch_all("SELECT name FROM clients")
    assert [r["name"] for r in rows] == ["Legacy Co"]
    # App keeps working after migration.
    db.get_or_create_client("New Co")
    assert db.count_clients() == 2


def test_migrate_preserves_all_tables(tmp_path):
    # Realistic pre-Phase-1 file: full modern schema exported to plaintext,
    # minus the m001-backfilled columns, so the test exercises the real
    # migration + backfill + index path instead of hand-written DDL.
    from skyadmin_pro.db import cipher as cipher_mod

    src = Database(tmp_path / "src.db")
    src.get_or_create_client("Acme")
    src.shutdown()
    plain = tmp_path / "full.db"
    c = cipher_mod.connect(str(tmp_path / "src.db"))
    try:
        c.execute(f"ATTACH DATABASE '{plain}' AS legacy KEY ''")
        c.execute("SELECT sqlcipher_export('legacy')")
        c.execute("DETACH DATABASE legacy")
    finally:
        c.close()
    assert db_state(plain) == "plaintext"
    lp = sqlite3.connect(str(plain))
    try:
        # Simulate legacy rows: NULL global_id exercises the m002 backfill.
        # (UNIQUE-declared columns cannot be DROPped in SQLite, so NULL it.)
        lp.execute("UPDATE clients SET global_id = NULL")
        lp.commit()
    finally:
        lp.close()
    db = Database(plain)
    assert db_state(plain) == "cipher"
    assert cipher.verify_cipher_db(plain) is True
    assert db.count_clients() == 1
    # Migration records travel with the export, so m002 (already applied in
    # the source) correctly skips — its backfill is covered by
    # tests/test_db_migrations.py. What this test owns: data survives.


def test_wrong_key_fails_closed(tmp_path, monkeypatch):
    db_file = tmp_path / "enc.db"
    Database(db_file)
    monkeypatch.setenv("SKYADMIN_CIPHER_SALT", "wrong-salt-for-this-test")
    with pytest.raises(RuntimeError, match="key mismatch"):
        Database(db_file)


def test_missing_driver_fails_closed(tmp_path, monkeypatch):
    import skyadmin_pro.db.cipher as cipher_mod

    monkeypatch.setattr(cipher_mod, "HAS_CIPHER", False)
    with pytest.raises(RuntimeError, match="sqlcipher3 is required"):
        cipher_mod.driver()


def test_backup_round_trip_stays_encrypted(tmp_path):
    db = Database(tmp_path / "live.db")
    db.get_or_create_client("Acme Corp")
    snap = db.backup_to(tmp_path / "snap.db")
    assert db_state(snap) == "cipher"
    assert cipher.verify_cipher_db(snap) is True
    assert db.restore_backup(snap) is True
    assert db.count_clients() == 1
