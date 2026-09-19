"""Conflict audit stores actor_winner / actor_loser / org_id (Wave 1b)."""

from __future__ import annotations

from skyadmin_pro.database import Database
from skyadmin_pro.services.data_sync.chunk_4 import log_sync_conflict
from skyadmin_pro.services.sync_hlc import hlc_actor


def test_hlc_actor_extracts_node():
    assert hlc_actor("0000000000123-0001-AABBCCDD") == "AABBCCDD"
    assert hlc_actor("") == ""
    assert hlc_actor(None) == ""


def test_log_sync_conflict_stores_actors_and_org(tmp_path):
    db = Database(tmp_path / "conflicts.db")
    db.set_setting("license_org_id", "firm:demo")
    log_sync_conflict(
        db,
        table="tasks",
        global_id="gid-1",
        direction="pull",
        local_updated_at="2026-01-01T00:00:00",
        remote_updated_at="2026-01-01T00:00:01",
        hlc_winner="0000000001000-0001-LOCALNODE",
        hlc_loser="0000000000900-0001-REMOTENODE",
    )
    rows = db.list_sync_conflicts(limit=10)
    assert len(rows) == 1
    row = rows[0]
    assert row["actor_winner"] == "LOCALNODE"
    assert row["actor_loser"] == "REMOTENODE"
    assert row["org_id"] == "firm:demo"
    assert row["hlc_winner"].endswith("LOCALNODE")
