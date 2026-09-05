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
    assert [int(row["version"]) for row in rows] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert rows[0]["name"] == "legacy_schema"
    assert rows[-1]["name"] == "perf_query_indexes"


def test_migrations_are_idempotent_on_reopen(db_path):
    Database(db_path)
    db = Database(db_path)
    count = db._fetch_one("SELECT COUNT(*) AS n FROM schema_migrations")["n"]
    assert count == 8


def test_new_migration_file_pattern(db_path):
    """Adding migration 009 should run once and be recorded."""
    from skyadmin_pro.db.migrations import runner
    from skyadmin_pro.db.migrations.runner import register_migrations

    marker = db_path.parent / "migration_009.ran"

    def upgrade(_db) -> None:
        marker.write_text("ok", encoding="utf-8")

    original = runner.MIGRATIONS
    try:
        register_migrations([*original, (9, "test_marker", upgrade)])
        db = Database(db_path)
        assert marker.read_text(encoding="utf-8") == "ok"
        row = db._fetch_one("SELECT name FROM schema_migrations WHERE version = 9")
        assert row["name"] == "test_marker"
        Database(db_path)
        assert marker.read_text(encoding="utf-8") == "ok"
    finally:
        register_migrations(original)
        if marker.exists():
            marker.unlink()
