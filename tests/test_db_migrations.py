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
    assert [int(row["version"]) for row in rows] == [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
    ]
    assert rows[0]["name"] == "legacy_schema"
    assert rows[11]["name"] == "sync_hlc"
    assert rows[16]["name"] == "documents_sync"
    assert rows[17]["name"] == "wave2b_sync"
    assert rows[18]["name"] == "sync_conflict_actors"
    assert rows[19]["name"] == "appointments"
    assert rows[20]["name"] == "drop_redundant_idx_clients_name"
    # m009 owns the group index (kept out of SCHEMA_SQL replay) — fresh DBs get it via migration.
    idx = db._fetch_all("SELECT name FROM sqlite_master WHERE type = 'index' AND name = 'idx_clients_group'")
    assert len(idx) == 1
    # m012 owns the HLC clocks (kept out of SCHEMA_SQL replay).
    cols = {row["name"] for row in db._fetch_all("PRAGMA table_info(clients)")}
    assert "hlc" in cols
    log_cols = {row["name"] for row in db._fetch_all("PRAGMA table_info(sync_conflicts)")}
    assert {"hlc_winner", "hlc_loser", "actor_winner", "actor_loser", "org_id"} <= log_cols


def test_migrations_are_idempotent_on_reopen(db_path):
    Database(db_path)
    db = Database(db_path)
    count = db._fetch_one("SELECT COUNT(*) AS n FROM schema_migrations")["n"]
    assert count == 21


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


def test_m021_drops_redundant_idx_clients_name(db_path):
    """Fresh DBs never carry the redundant binary idx_clients_name; legacy DBs drop it via m021."""
    db = Database(db_path)
    names = {
        row["name"]
        for row in db._fetch_all("SELECT name FROM sqlite_master WHERE type = 'index' AND name = 'idx_clients_name'")
    }
    assert "idx_clients_name" not in names

    # Simulate a legacy DB that still has the redundant index; clear the m021 marker.
    with db.connection() as conn:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name)")
        conn.execute("DELETE FROM schema_migrations WHERE version = 21")
    reopen = Database(db_path)
    names = {
        row["name"]
        for row in reopen._fetch_all(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND name = 'idx_clients_name'"
        )
    }
    assert "idx_clients_name" not in names
    # NOCASE UNIQUE auto-index still serves name lookups.
    cid = reopen.get_or_create_client("Drop Probe Co")
    assert reopen.client_id_by_name("drop probe co") == cid


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


def test_m011_adds_client_groups_sync_columns(db_path):
    """Legacy client_groups without sync columns gain global_id / updated_at / deleted_at."""
    db = Database(db_path)
    gid = db.add_client_group("Pre-sync")
    with db.connection() as conn:
        # Simulate pre-m011 shape by clearing migration marker only if columns exist —
        # delete m011 and recreate minimal table without sync cols.
        conn.execute("DELETE FROM schema_migrations WHERE version = 11")
        conn.execute("DROP TABLE client_groups")
        conn.execute(
            """
            CREATE TABLE client_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                color TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        conn.execute("INSERT INTO client_groups (name) VALUES ('Legacy Group')")

    reopened = Database(db_path)
    with reopened.connection() as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(client_groups)")}
        row = conn.execute("SELECT global_id, updated_at FROM client_groups WHERE name = 'Legacy Group'").fetchone()
    assert {"global_id", "updated_at", "deleted_at"} <= cols
    assert row["global_id"]
    assert row["updated_at"]
    marker = reopened._fetch_one("SELECT name FROM schema_migrations WHERE version = 11")
    assert marker["name"] == "client_groups_sync"
    # original add still usable after reopen path
    assert gid  # silence unused if recreate wiped it


def test_fresh_db_search_uses_fts_match(db_path):
    """Fresh installs get clients_fts from base schema — MATCH path, not LIKE fallback."""
    db = Database(db_path)
    tables = {row["name"] for row in db._fetch_all("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "clients_fts" in tables
    client_id = db.get_or_create_client("FTS Probe Company")
    hits = db._fetch_all("SELECT rowid AS id FROM clients_fts WHERE clients_fts MATCH 'probe*'")
    assert [int(r["id"]) for r in hits] == [client_id]
    assert db.search_clients("probe")[0]["id"] == client_id


def test_m010_heals_stale_fts(db_path):
    """A clients_fts missing rows (dead triggers era) is rebuilt by m010."""
    db = Database(db_path)
    cid = db.get_or_create_client("Stale FTS Co")
    with db.connection() as conn:
        conn.execute("DELETE FROM clients_fts WHERE rowid = ?", (cid,))
    assert db._fetch_all("SELECT rowid AS id FROM clients_fts WHERE clients_fts MATCH 'stale*'") == []
    with db.connection() as conn:
        conn.execute("DELETE FROM schema_migrations WHERE version = 10")
    Database(db_path)  # reopen triggers pending m010
    hits = db._fetch_all("SELECT rowid AS id FROM clients_fts WHERE clients_fts MATCH 'stale*'")
    assert [int(r["id"]) for r in hits] == [cid]


def test_m015_adds_pnd_monthly_annual_columns(db_path):
    """Fresh and upgraded DBs expose pnd1/3/90/91 status columns."""
    db = Database(db_path)
    cols = {row["name"] for row in db._fetch_all("PRAGMA table_info(clients)")}
    assert {"pnd1_status", "pnd3_status", "pnd90_status", "pnd91_status"} <= cols
    row = db._fetch_one("SELECT name FROM schema_migrations WHERE version = 15")
    assert row["name"] == "pnd_monthly_annual"


def test_m016_adds_credential_sync_columns(db_path):
    """Wave E — client/office credentials gain global_id, deleted_at, hlc."""
    db = Database(db_path)
    for table in ("client_credentials", "office_credentials"):
        cols = {row["name"] for row in db._fetch_all(f"PRAGMA table_info({table})")}
        assert {"global_id", "deleted_at", "hlc"} <= cols
    row = db._fetch_one("SELECT name FROM schema_migrations WHERE version = 16")
    assert row["name"] == "credentials_sync"


def test_m017_adds_document_sync_columns(db_path):
    """Wave 2a — documents / financial_documents sync + drive_file_id metadata."""
    db = Database(db_path)
    needed = {
        "global_id",
        "deleted_at",
        "updated_at",
        "hlc",
        "drive_file_id",
        "drive_parent_path",
        "content_hash",
        "byte_size",
        "mime_type",
        "original_filename",
    }
    for table in ("documents", "financial_documents"):
        cols = {row["name"] for row in db._fetch_all(f"PRAGMA table_info({table})")}
        assert needed <= cols
    row = db._fetch_one("SELECT name FROM schema_migrations WHERE version = 17")
    assert row["name"] == "documents_sync"


def test_m018_adds_wave2b_sync_columns(db_path):
    """Wave 2b — pipeline/suppliers/courier/tax calendar sync columns."""
    db = Database(db_path)
    needed = {"global_id", "deleted_at", "updated_at", "hlc"}
    tables = (
        "pipeline_items",
        "suppliers",
        "supplier_payments",
        "supplier_services",
        "courier_logs",
        "client_months",
        "renewal_items",
        "tax_cycle_log",
        "recurring_tasks",
    )
    for table in tables:
        cols = {row["name"] for row in db._fetch_all(f"PRAGMA table_info({table})")}
        assert needed <= cols, table
    row = db._fetch_one("SELECT name FROM schema_migrations WHERE version = 18")
    assert row["name"] == "wave2b_sync"


def test_run_monthly_cycle_flips_only_monthly_fields(db_path):
    from skyadmin_pro.config import MONTHLY_TAX_TYPES

    db = Database(db_path)
    cid = db.get_or_create_client("Cycle Co")
    db.update_client_fields(
        cid,
        service_type=MONTHLY_TAX_TYPES[0],
        pnd1_status="Pending",
        pnd53_status="Pending",
        pnd90_status="Pending",
        fs_status="Pending",
        audit_status="Pending",
    )
    result = db.run_monthly_cycle()
    assert result["fields_updated"] == 2
    client = db.get_client(cid)
    assert client["pnd1_status"] == "On-Going"
    assert client["pnd53_status"] == "On-Going"
    assert client["pnd90_status"] == "Pending"
    assert client["fs_status"] == "Pending"
    assert client["audit_status"] == "Pending"
