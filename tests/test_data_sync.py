"""P4 data sync — local apply + HTTP client."""

import json
import uuid

from skyadmin_pro.config import SETTING_DATA_SYNC_ENABLED, SETTING_SYNC_LAST_PULL, SETTING_SYNC_LAST_PUSH
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


def test_collect_and_apply_client_groups_via_global_id(db):
    """client_groups sync by global_id; clients carry group_global_id (not numeric group_id)."""
    gid = uuid.uuid4().hex
    group_id = db.add_client_group("VIP")
    group = db._fetch_one("SELECT global_id FROM client_groups WHERE id = ?", (group_id,))
    assert group and group["global_id"]
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO clients (name, global_id, group_id, updated_at) VALUES (?, ?, ?, ?)",
            ("Grouped Co", gid, group_id, "2026-06-01 10:00:00"),
        )
    changes = sync.collect_local_changes(db)
    group_change = next(c for c in changes if c["table"] == "client_groups")
    assert group_change["row"]["name"] == "VIP"
    assert "id" not in group_change["row"]
    client_change = next(c for c in changes if c["global_id"] == gid)
    assert "group_id" not in client_change["row"]
    assert client_change["row"].get("group_global_id") == group["global_id"]

    remote_group_gid = uuid.uuid4().hex
    remote_client_gid = uuid.uuid4().hex
    applied, conflicts = sync.apply_remote_changes(
        db,
        [
            {
                "table": "client_groups",
                "global_id": remote_group_gid,
                "updated_at": "2026-06-02T09:00:00",
                "deleted_at": None,
                "row": {
                    "global_id": remote_group_gid,
                    "name": "Remote VIP",
                    "color": None,
                    "updated_at": "2026-06-02T09:00:00",
                },
            },
            {
                "table": "clients",
                "global_id": remote_client_gid,
                "updated_at": "2026-06-02T10:00:00",
                "deleted_at": None,
                "row": {
                    "global_id": remote_client_gid,
                    "name": "Remote Grouped",
                    "status": "active",
                    "group_global_id": remote_group_gid,
                    "updated_at": "2026-06-02T10:00:00",
                },
            },
        ],
    )
    assert (applied, conflicts) == (2, 0)
    remote_group = db._fetch_one(
        "SELECT id, name FROM client_groups WHERE global_id = ?",
        (remote_group_gid,),
    )
    assert remote_group["name"] == "Remote VIP"
    row = db._fetch_one(
        "SELECT name, group_id FROM clients WHERE global_id = ?",
        (remote_client_gid,),
    )
    assert row["name"] == "Remote Grouped"
    assert row["group_id"] == remote_group["id"]

    # Numeric group_id in a remote payload must still be ignored
    stray_gid = uuid.uuid4().hex
    sync.apply_remote_changes(
        db,
        [
            {
                "table": "clients",
                "global_id": stray_gid,
                "updated_at": "2026-06-03T10:00:00",
                "deleted_at": None,
                "row": {
                    "global_id": stray_gid,
                    "name": "Stray",
                    "status": "active",
                    "group_id": group_id,
                    "updated_at": "2026-06-03T10:00:00",
                },
            },
        ],
    )
    stray = db._fetch_one("SELECT group_id FROM clients WHERE global_id = ?", (stray_gid,))
    assert stray["group_id"] is None


def test_sync_pull_paginates_until_short_page(db, monkeypatch):
    """Large pulls request multiple Worker pages and report page count."""
    monkeypatch.setattr(sync, "SYNC_PULL_PAGE_SIZE", 2)
    pages = [
        {
            "ok": True,
            "server_time": "2026-06-01T12:00:00Z",
            "changes": [
                {
                    "table": "clients",
                    "global_id": "g0",
                    "updated_at": "2026-06-01T11:00:00Z",
                    "deleted_at": None,
                    "row": {
                        "global_id": "g0",
                        "name": "Co 0",
                        "status": "active",
                        "updated_at": "2026-06-01T11:00:00Z",
                    },
                },
                {
                    "table": "clients",
                    "global_id": "g1",
                    "updated_at": "2026-06-01T11:00:01Z",
                    "deleted_at": None,
                    "row": {
                        "global_id": "g1",
                        "name": "Co 1",
                        "status": "active",
                        "updated_at": "2026-06-01T11:00:01Z",
                    },
                },
            ],
        },
        {
            "ok": True,
            "server_time": "2026-06-01T12:00:01Z",
            "changes": [
                {
                    "table": "clients",
                    "global_id": "g-last",
                    "updated_at": "2026-06-01T11:01:00Z",
                    "deleted_at": None,
                    "row": {
                        "global_id": "g-last",
                        "name": "Last Co",
                        "status": "active",
                        "updated_at": "2026-06-01T11:01:00Z",
                    },
                }
            ],
        },
    ]
    calls: list[str] = []

    def fake_request(method, path, **kwargs):
        if method == "GET" and path == "/api/sync/pull":
            calls.append(kwargs.get("query") or "")
            return True, pages.pop(0)
        if method == "POST" and path == "/api/sync/push":
            return True, {
                "ok": True,
                "applied": 0,
                "conflicts": 0,
                "server_time": "2026-06-01T12:00:01Z",
            }
        return False, "unexpected"

    monkeypatch.setattr(sync, "is_data_sync_enabled", lambda _db: True)
    monkeypatch.setattr(sync, "ensure_sync_credentials", lambda **_kw: ("MID", "tok"))
    monkeypatch.setattr(sync, "get_machine_id", lambda: "MID")
    monkeypatch.setattr(sync, "_sync_request", fake_request)
    monkeypatch.setattr(sync, "API_BASE_URL", "https://example.test")

    ok, msg = sync.sync_data(db, timeout=5)
    assert ok
    assert "pulled 3" in msg
    assert "2 pull pages" in msg
    assert len(calls) == 2
    assert "limit=2" in calls[0]
    assert "since=" in calls[1]


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
    assert db.get_setting(SETTING_SYNC_LAST_PUSH) == "2026-04-01 08:00:00"
    assert any("/api/sync/pull" in u for u in calls)
    assert any("/api/sync/push" in u for u in calls)


def test_collect_local_changes_global_limit(db):
    """Global batch size truncates across tables, not 500-per-table."""
    with db.connection() as conn:
        for i in range(5):
            conn.execute(
                "INSERT INTO clients (name, global_id, updated_at) VALUES (?, ?, ?)",
                (f"C{i}", uuid.uuid4().hex, f"2026-07-01 10:00:0{i}"),
            )
            conn.execute(
                """
                INSERT INTO tasks (title, status, global_id, updated_at)
                VALUES (?, 'pending', ?, ?)
                """,
                (f"T{i}", uuid.uuid4().hex, f"2026-07-01 11:00:0{i}"),
            )
    changes = sync.collect_local_changes(db, limit=3)
    assert len(changes) == 3
    assert [c["updated_at"] for c in changes] == sorted(c["updated_at"] for c in changes)


def test_sync_push_paginates_until_drained(db, monkeypatch, fake_app_dir):
    """Large local change sets push in multiple HTTP batches."""
    import json
    import urllib.request

    import skyadmin_pro.config as config
    import skyadmin_pro.paths as paths_mod

    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_app_dir)
    monkeypatch.setattr(config, "API_BASE_URL", "https://worker.test")
    monkeypatch.setattr(sync, "SYNC_PUSH_PAGE_SIZE", 2)
    sync.save_sync_credentials("TESTMACHINE00001", "tok")
    monkeypatch.setattr(sync, "get_machine_id", lambda: "TESTMACHINE00001")

    with db.connection() as conn:
        for i in range(5):
            conn.execute(
                "INSERT INTO clients (name, global_id, updated_at) VALUES (?, ?, ?)",
                (f"Push {i}", uuid.uuid4().hex, f"2026-08-01 12:00:0{i}"),
            )

    push_bodies: list[list] = []

    def fake_urlopen(req, timeout=0):
        if "/api/sync/pull" in req.full_url:
            body = json.dumps({"ok": True, "server_time": "2026-08-01T13:00:00Z", "changes": []}).encode()
        else:
            raw = req.data or b"{}"
            payload = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
            push_bodies.append(payload.get("changes") or [])
            body = json.dumps(
                {
                    "ok": True,
                    "applied": len(payload.get("changes") or []),
                    "conflicts": 0,
                    "server_time": "2026-08-01T13:00:00Z",
                }
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
    assert "3 push pages" in msg
    assert len(push_bodies) == 3
    assert [len(b) for b in push_bodies] == [2, 2, 1]
    assert db.get_setting(SETTING_SYNC_LAST_PUSH) == "2026-08-01 12:00:04"
    assert db.get_setting(SETTING_SYNC_LAST_PULL) == "2026-08-01T13:00:00Z"


def test_sync_data_push_upgrade_required_prompts_update(db, monkeypatch, fake_app_dir):
    import io
    import urllib.error
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

    def fake_urlopen(req, timeout=0):
        if "/api/sync/pull" in req.full_url:
            body = json.dumps({"ok": True, "server_time": "2026-04-01T09:00:00Z", "changes": []}).encode()
        else:
            err_body = json.dumps({"ok": False, "error": "upgrade-required", "legacy": 1}).encode()
            raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {}, io.BytesIO(err_body))

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
    assert not ok
    assert "latest" in msg
