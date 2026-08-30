"""P4 data sync — local apply + HTTP client."""

import json
import uuid

import pytest

from skyadmin_pro.config import SETTING_SYNC_LAST_PULL
from skyadmin_pro.services import data_sync as sync


def test_ensure_sync_ids_assigns_global_ids(db):
    with db.connection() as conn:
        conn.execute("INSERT INTO clients (name) VALUES ('Acme')")
    sync.ensure_sync_ids(db)
    row = db._fetch_one("SELECT global_id FROM clients WHERE name = 'Acme'")
    assert row and row["global_id"]


def test_apply_remote_client_inserts(db):
    gid = uuid.uuid4().hex
    change = {
        "table": "clients",
        "global_id": gid,
        "updated_at": "2026-01-02T10:00:00",
        "deleted_at": None,
        "row": {
            "global_id": gid,
            "name": "Remote Co",
            "status": "active",
            "updated_at": "2026-01-02T10:00:00",
        },
    }
    assert sync.apply_remote_changes(db, [change]) == (1, 0)
    row = db._fetch_one("SELECT name FROM clients WHERE global_id = ?", (gid,))
    assert row["name"] == "Remote Co"


def test_apply_remote_strips_forbidden_columns(db):
    gid = uuid.uuid4().hex
    change = {
        "table": "clients",
        "global_id": gid,
        "updated_at": "2026-01-02T10:00:00",
        "deleted_at": None,
        "row": {
            "global_id": gid,
            "name": "Safe Co",
            "status": "active",
            "ird_password": "stolen",
            "hacker_field": "ignored",
            "updated_at": "2026-01-02T10:00:00",
        },
    }
    assert sync.apply_remote_changes(db, [change]) == (1, 0)
    row = db._fetch_one("SELECT name, ird_password FROM clients WHERE global_id = ?", (gid,))
    assert row["name"] == "Safe Co"
    assert not row["ird_password"]


def test_lww_skips_older_remote(db):
    gid = uuid.uuid4().hex
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO clients (name, global_id, updated_at) VALUES (?, ?, ?)",
            ("Local", gid, "2026-02-01 12:00:00"),
        )
    change = {
        "table": "clients",
        "global_id": gid,
        "updated_at": "2026-01-01 12:00:00",
        "row": {"global_id": gid, "name": "Stale", "status": "active", "updated_at": "2026-01-01 12:00:00"},
    }
    assert sync.apply_remote_changes(db, [change]) == (0, 1)
    row = db._fetch_one("SELECT name FROM clients WHERE global_id = ?", (gid,))
    assert row["name"] == "Local"
    conflict = db._fetch_one(
        "SELECT direction, remote_updated_at FROM sync_conflicts WHERE global_id = ?",
        (gid,),
    )
    assert conflict and conflict["direction"] == "pull"


def test_count_sync_conflicts(db):
    assert db.count_sync_conflicts() == 0
    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO sync_conflicts (table_name, global_id, direction, local_updated_at, remote_updated_at)
            VALUES ('clients', 'abc', 'pull', '2026-01-01', '2026-01-02')
            """
        )
    assert db.count_sync_conflicts() == 1
    rows = db.list_sync_conflicts()
    assert len(rows) == 1
    assert rows[0]["global_id"] == "abc"
    assert db.clear_sync_conflicts() == 1
    assert db.count_sync_conflicts() == 0


def test_collect_includes_soft_delete_tombstones(db):
    gid = uuid.uuid4().hex
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO clients (name, global_id, updated_at, deleted_at) VALUES (?, ?, ?, ?)",
            ("Gone Co", gid, "2026-05-01 10:00:00", "2026-05-01 10:00:00"),
        )
    changes = sync.collect_local_changes(db)
    tombstone = next(c for c in changes if c["global_id"] == gid)
    assert tombstone["deleted_at"] == "2026-05-01 10:00:00"
    assert tombstone["row"] == {"global_id": gid}


def test_apply_remote_tombstone_marks_deleted(db):
    gid = uuid.uuid4().hex
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO clients (name, global_id, updated_at) VALUES (?, ?, ?)",
            ("Soon Gone", gid, "2026-05-01 09:00:00"),
        )
    change = {
        "table": "clients",
        "global_id": gid,
        "updated_at": "2026-05-01 10:00:00",
        "deleted_at": "2026-05-01 10:00:00",
        "row": {"global_id": gid},
    }
    assert sync.apply_remote_changes(db, [change]) == (1, 0)
    row = db._fetch_one("SELECT deleted_at FROM clients WHERE global_id = ?", (gid,))
    assert row["deleted_at"] == "2026-05-01 10:00:00"


    gid = uuid.uuid4().hex
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO clients (name, global_id, ird_password, updated_at) VALUES (?, ?, ?, ?)",
            ("Secret Co", gid, "plain-secret", "2026-03-01 09:00:00"),
        )
    changes = sync.collect_local_changes(db)
    client_change = next(c for c in changes if c["global_id"] == gid)
    assert "ird_password" not in client_change["row"]


def test_sync_data_skips_without_api(db, monkeypatch):
    monkeypatch.setattr(sync, "API_BASE_URL", "")
    ok, msg = sync.sync_data(db)
    assert ok
    assert "skipped" in msg.lower()


def test_register_sync_device_persists_credentials(monkeypatch, fake_app_dir):
    import urllib.request

    import skyadmin_pro.config as config
    import skyadmin_pro.paths as paths_mod

    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_app_dir)
    monkeypatch.setattr(config, "API_BASE_URL", "https://worker.test")

    class FakeResp:
        def read(self, n=-1):
            return json.dumps(
                {"ok": True, "machine_id": "ABCD1234EFGH5678", "sync_token": "tok123"}
            ).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=0: FakeResp())
    monkeypatch.setattr(sync, "_license_code", lambda: "fake-license")

    ok, _msg = sync.register_sync_device()
    assert ok
    creds = sync.load_sync_credentials()
    assert creds == ("ABCD1234EFGH5678", "tok123")


def test_sync_data_pull_push_updates_cursor(db, monkeypatch, fake_app_dir):
    import urllib.request

    import skyadmin_pro.config as config
    import skyadmin_pro.paths as paths_mod

    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_app_dir)
    monkeypatch.setattr(config, "API_BASE_URL", "https://worker.test")
    sync.save_sync_credentials("TESTMACHINE00001", "tok")
    monkeypatch.setattr(sync, "get_machine_id", lambda: "TESTMACHINE00001")

    gid = uuid.uuid4().hex
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO clients (name, global_id, updated_at) VALUES (?, ?, ?)",
            ("Push Me", gid, "2026-04-01 08:00:00"),
        )

    calls: list[str] = []

    def fake_urlopen(req, timeout=0):
        calls.append(req.full_url)
        if "/api/sync/pull" in req.full_url:
            body = json.dumps({"ok": True, "server_time": "2026-04-01T09:00:00Z", "changes": []}).encode()
        else:
            body = json.dumps({"ok": True, "applied": 1, "conflicts": 0, "server_time": "2026-04-01T09:00:00Z"}).encode()

        class R:
            def read(self, n=-1):
                return body

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return R()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    ok, msg = sync.sync_data(db)
    assert ok, msg
    assert db.get_setting(SETTING_SYNC_LAST_PULL) == "2026-04-01T09:00:00Z"
    assert any("/api/sync/pull" in u for u in calls)
    assert any("/api/sync/push" in u for u in calls)
