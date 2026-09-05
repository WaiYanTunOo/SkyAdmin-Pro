"""Versioned schema_migrations runner."""

from __future__ import annotations

import pytest

from skyadmin_pro.database import Database


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "migrations.db"


def test_fresh_database_records_all_migrations(db_path):
    db = Database(db_path)
    rows = db._fetch_all("SELECT version, name FROM schema_migrations ORDER BY version")
    assert [int(row["version"]) for row in rows] == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert rows[0]["name"] == "legacy_schema"
    assert rows[-1]["name"] == "client_groups"
    # m009 owns the group index (kept out of SCHEMA_SQL replay) — fresh DBs get it via migration.
    idx = db._fetch_all("SELECT name FROM sqlite_master WHERE type = 'index' AND name = 'idx_clients_group'")
    assert len(idx) == 1


def test_migrations_are_idempotent_on_reopen(db_path):
    Database(db_path)
    db = Database(db_path)
    count = db._fetch_one("SELECT COUNT(*) AS n FROM schema_migrations")["n"]
    assert count == 9


def test_new_migration_file_pattern(db_path):
    """Adding migration 099 should run once and be recorded."""
    from skyadmin_pro.db.migrations import runner
    from skyadmin_pro.db.migrations.runner import register_migrations

    marker = db_path.parent / "migration_099.ran"

    def upgrade(_db) -> None:
        marker.write_text("ok", encoding="utf-8")

    original = runner.MIGRATIONS
    try:
        register_migrations([*original, (99, "test_marker", upgrade)])
        db = Database(db_path)
        assert marker.read_text(encoding="utf-8") == "ok"
        row = db._fetch_one("SELECT name FROM schema_migrations WHERE version = 99")
        assert row["name"] == "test_marker"
        Database(db_path)
        assert marker.read_text(encoding="utf-8") == "ok"
    finally:
        register_migrations(original)
        if marker.exists():
            marker.unlink()


def test_m009_upgrades_legacy_db_missing_group_id(db_path):
    """Legacy DBs (no client_groups table, no group_id column) gain both via m009."""
    db = Database(db_path)
    client_id = db.get_or_create_client("Legacy Co")
    with db.connection() as conn:
        conn.execute("DROP TABLE client_groups")
        conn.execute("DROP INDEX IF EXISTS idx_clients_group")
        conn.execute("ALTER TABLE clients DROP COLUMN group_id")
        conn.execute("DELETE FROM schema_migrations WHERE version = 9")

    reopened = Database(db_path)  # triggers pending m009
    with reopened.connection() as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        cols = {row[1] for row in conn.execute("PRAGMA table_info(clients)")}
    assert "client_groups" in tables
    assert "group_id" in cols
    assert reopened.get_client(client_id)["name"] == "Legacy Co"
    row = reopened._fetch_one("SELECT name FROM schema_migrations WHERE version = 9")
    assert row["name"] == "client_groups"


def test_fresh_db_search_uses_fts_match(db_path):
    """Fresh installs get clients_fts from base schema — MATCH path, not LIKE fallback."""
    db = Database(db_path)
    tables = {
        row["name"]
        for row in db._fetch_all("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert "clients_fts" in tables
    client_id = db.get_or_create_client("FTS Probe Company")
    hits = db._fetch_all("SELECT rowid AS id FROM clients_fts WHERE clients_fts MATCH 'probe*'")
    assert [int(r["id"]) for r in hits] == [client_id]
    assert db.search_clients("probe")[0]["id"] == client_id
