"""F1.5 — local audit list helpers (tax cycle + sync conflicts)."""

from __future__ import annotations


def test_list_tax_cycle_log(db):
    cid = db.get_or_create_client("Audit Tax Co")
    db.log_tax_change(cid, "fs_status", "Pending", "Completed")
    db.log_tax_change(cid, "pnd53_status", "Pending", "On-Going")

    rows = db.list_tax_cycle_log(limit=10)
    assert len(rows) >= 2
    assert rows[0]["log_type"] == "tax_change"
    assert rows[0]["client_name"] == "Audit Tax Co"
    fields = {r["field"] for r in rows}
    assert "fs_status" in fields
    assert "pnd53_status" in fields


def test_list_sync_conflicts_and_audit_unified(db):
    cid = db.get_or_create_client("Audit Sync Co")
    db.log_tax_change(cid, "pp30_status", "Pending", "Complete")
    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO sync_conflicts
                (table_name, global_id, direction, local_updated_at, remote_updated_at)
            VALUES ('clients', 'gid-audit-1', 'pull', '2026-01-01', '2026-01-02')
            """
        )

    conflicts = db.list_sync_conflicts(limit=50)
    assert len(conflicts) == 1
    assert conflicts[0]["global_id"] == "gid-audit-1"

    tax_only = db.list_audit_log(limit=50, log_type="tax_change")
    assert tax_only and all(r["log_type"] == "tax_change" for r in tax_only)

    sync_only = db.list_audit_log(limit=50, log_type="sync_conflict")
    assert len(sync_only) == 1
    assert sync_only[0]["log_type"] == "sync_conflict"

    all_rows = db.list_audit_log(limit=50)
    types = {r["log_type"] for r in all_rows}
    assert "tax_change" in types
    assert "sync_conflict" in types


def test_list_helpers_tolerate_missing_tables(db):
    with db.connection() as conn:
        conn.execute("DROP TABLE IF EXISTS sync_conflicts")
        conn.execute("DROP TABLE IF EXISTS tax_cycle_log")

    assert db.list_sync_conflicts() == []
    assert db.count_sync_conflicts() == 0
    assert db.clear_sync_conflicts() == 0
    assert db.list_tax_cycle_log() == []
    assert db.list_audit_log() == []
