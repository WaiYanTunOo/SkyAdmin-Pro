"""P4 data sync — local apply + HTTP client."""

import json
import uuid

from skyadmin_pro.config import SETTING_DATA_SYNC_ENABLED, SETTING_SYNC_LAST_PULL
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


def test_log_sync_conflict_dedupes(db):
    sync.log_sync_conflict(
        db,
        table="clients",
        global_id="abc",
        direction="pull",
        local_updated_at="2026-01-03",
        remote_updated_at="2026-01-02",
    )
    sync.log_sync_conflict(
        db,
        table="clients",
        global_id="abc",
        direction="pull",
        local_updated_at="2026-01-04",
        remote_updated_at="2026-01-02",
    )
    assert db.count_sync_conflicts() == 1


def test_sync_data_disabled_by_default(db, monkeypatch):
    monkeypatch.setattr(sync, "API_BASE_URL", "https://worker.test")
    ok, msg = sync.sync_data(db)
    assert ok
    assert "off" in msg.lower() or "disabled" in msg.lower()


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
    from skyadmin_pro.services.secret_fields import is_encrypted_secret

    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_app_dir)
    monkeypatch.setattr(config, "API_BASE_URL", "https://worker.test")
    monkeypatch.setattr(
        "skyadmin_pro.services.secret_fields.get_machine_id",
        lambda: "ABCD1234EFGH5678",
    )

    class FakeResp:
        def read(self, n=-1):
            return json.dumps({"ok": True, "machine_id": "ABCD1234EFGH5678", "sync_token": "tok123"}).encode()

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

    on_disk = (fake_app_dir / "sync_device.json").read_text(encoding="utf-8")
    assert on_disk.startswith("SKYSECRET1:")
    assert is_encrypted_secret(on_disk)
    assert "tok123" not in on_disk
    assert "ABCD1234EFGH5678" not in on_disk


def test_save_sync_credentials_writes_ciphertext_on_disk(monkeypatch, fake_app_dir):
    import skyadmin_pro.paths as paths_mod
    from skyadmin_pro.services.secret_fields import is_encrypted_secret

    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_app_dir)
    monkeypatch.setattr(
        "skyadmin_pro.services.secret_fields.get_machine_id",
        lambda: "TESTMACHINE00001",
    )
    sync.save_sync_credentials("TESTMACHINE00001", "super-secret-token")
    raw = (fake_app_dir / "sync_device.json").read_text(encoding="utf-8")
    assert raw.startswith("SKYSECRET1:")
    assert is_encrypted_secret(raw)
    assert "super-secret-token" not in raw
    assert sync.load_sync_credentials() == ("TESTMACHINE00001", "super-secret-token")


def test_collect_and_apply_syncs_client_group_id(db):
    gid = uuid.uuid4().hex
    group_id = db.add_client_group("VIP")
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO clients (name, global_id, group_id, updated_at) VALUES (?, ?, ?, ?)",
            ("Grouped Co", gid, group_id, "2026-06-01 10:00:00"),
        )
    changes = sync.collect_local_changes(db)
    client_change = next(c for c in changes if c["global_id"] == gid)
    assert client_change["row"].get("group_id") == group_id

    remote_gid = uuid.uuid4().hex
    change = {
        "table": "clients",
        "global_id": remote_gid,
        "updated_at": "2026-06-02T10:00:00",
        "deleted_at": None,
        "row": {
            "global_id": remote_gid,
            "name": "Remote Grouped",
            "status": "active",
            "group_id": group_id,
            "updated_at": "2026-06-02T10:00:00",
        },
    }
    assert sync.apply_remote_changes(db, [change]) == (1, 0)
    row = db._fetch_one("SELECT name, group_id FROM clients WHERE global_id = ?", (remote_gid,))
    assert row["name"] == "Remote Grouped"
    assert row["group_id"] == group_id


def test_rotate_sync_credentials_after_license_change(monkeypatch, fake_app_dir):
    import urllib.request

    import skyadmin_pro.config as config
    import skyadmin_pro.paths as paths_mod

    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_app_dir)
    monkeypatch.setattr(config, "API_BASE_URL", "https://worker.test")
    sync.save_sync_credentials("ABCD1234EFGH5678", "old-token")
    monkeypatch.setattr(sync, "_license_code", lambda: "fake-license")

    class FakeResp:
        def __init__(self, token: str):
            self._token = token

        def read(self, n=-1):
            return json.dumps({"ok": True, "machine_id": "ABCD1234EFGH5678", "sync_token": self._token}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    tokens = iter(["new-token-1", "new-token-2"])

    def fake_urlopen(req, timeout=0):
        return FakeResp(next(tokens))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    ok, msg = sync.rotate_sync_credentials_after_license_change()
    assert ok, msg
    assert sync.load_sync_credentials() == ("ABCD1234EFGH5678", "new-token-1")


def test_rotate_sync_skips_when_no_credentials(monkeypatch, fake_app_dir):
    import skyadmin_pro.paths as paths_mod

    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_app_dir)
    calls: list[str] = []

    def fail_register(*_a, **_k):
        calls.append("register")
        return False, "should not run"

    monkeypatch.setattr(sync, "register_sync_device", fail_register)
    ok, msg = sync.rotate_sync_credentials_after_license_change()
    assert ok
    assert "No sync credentials" in msg
    assert calls == []


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
            body = json.dumps(
                {"ok": True, "applied": 1, "conflicts": 0, "server_time": "2026-04-01T09:00:00Z"}
            ).encode()

        class R:
            def read(self, n=-1):
                return body

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return R()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    db.set_setting(SETTING_DATA_SYNC_ENABLED, "1")
    ok, msg = sync.sync_data(db)
    assert ok, msg
    assert db.get_setting(SETTING_SYNC_LAST_PULL) == "2026-04-01T09:00:00Z"
    assert any("/api/sync/pull" in u for u in calls)
    assert any("/api/sync/push" in u for u in calls)
