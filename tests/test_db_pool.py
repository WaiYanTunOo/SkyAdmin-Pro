"""Connection pooling tests — verify PoolMixin behaves correctly."""

from __future__ import annotations

import threading

import pytest


def test_pooled_conn_reused_on_main_thread(tmp_path):
    """Main thread gets the same connection on repeated calls."""
    from skyadmin_pro.database import Database

    db = Database(tmp_path / "pool_test.db")
    conn1 = db._get_pooled_conn()
    conn2 = db._get_pooled_conn()
    assert conn1 is conn2
    db.shutdown()


def test_different_threads_get_different_conns(tmp_path):
    """Each thread gets its own connection."""
    from skyadmin_pro.database import Database

    db = Database(tmp_path / "pool_test.db")
    main_conn = db._get_pooled_conn()

    other_conn: list = []

    def fetch_in_thread():
        other_conn.append(db._get_bg_conn())

    t = threading.Thread(target=fetch_in_thread)
    t.start()
    t.join()

    assert len(other_conn) == 1
    assert other_conn[0] is not main_conn
    db.shutdown()


def test_pooled_conn_validates_liveness(tmp_path):
    """Stale connections are closed and replaced."""
    from skyadmin_pro.database import Database

    db = Database(tmp_path / "pool_test.db")
    conn1 = db._get_pooled_conn()
    assert conn1 is db._pooled_conn

    # Close the pooled connection externally to simulate staleness
    try:
        conn1.close()
    except Exception:
        pass

    db._pooled_conn = conn1  # simulate stale reference
    conn2 = db._get_pooled_conn()
    # A new connection should have been created since the old one is dead
    assert conn2 is not conn1
    db.shutdown()


def test_restore_lockout_raises(monkeypatch, tmp_path):
    """_get_pooled_conn raises when restore lockout is active."""
    from skyadmin_pro.database import Database

    db = Database(tmp_path / "pool_test.db")
    db._restore_lockout = True

    with pytest.raises(RuntimeError, match="locked for restore"):
        db._get_pooled_conn()

    db.shutdown()


def test_bundle_active_tracking(tmp_path):
    """_bundle_active returns True when a bundle connection is pinned."""
    from skyadmin_pro.database import Database

    db = Database(tmp_path / "pool_test.db")
    assert not db._bundle_active()
    # _bundle_conn is None by default on a fresh database
    assert db._bundle_conn is None
    db.shutdown()


def test_dashboard_snapshot_uses_one_connection(tmp_path, monkeypatch):
    """dashboard_snapshot runs across a single pooled connection."""
    from skyadmin_pro.database import Database

    db = Database(tmp_path / "pool_test.db")
    calls = []
    real_connect = db._connect

    def counting_connect():
        calls.append(1)
        return real_connect()

    monkeypatch.setattr(db, "_connect", counting_connect)
    snapshot = db.dashboard_snapshot()
    assert snapshot is not None
    assert len(calls) <= 1, f"dashboard_snapshot opened {len(calls)} connections"
    db.shutdown()


def test_background_conns_closed_on_shutdown(tmp_path):
    """Deterministic cleanup: _close_pooled_conn closes every bg connection.

    Each background thread acquires its own handle and parks; after the main
    thread closes the pool, each parked thread probes its own handle. A
    closed SQLite connection raises when used, so a successful probe means
    the handle survived the close (the leak we are guarding against).
    """
    from skyadmin_pro.database import Database

    db = Database(tmp_path / "pool_test.db")
    release = threading.Event()
    acquired: list = []
    results: list = []

    def worker():
        conn = db._get_bg_conn()
        acquired.append(conn)
        if not release.wait(15):
            return
        try:
            conn.execute("SELECT 1")
            results.append(False)
        except Exception:
            results.append(True)

    threads = [threading.Thread(target=worker) for _ in range(3)]
    for t in threads:
        t.start()
    for _ in range(150):
        if len(acquired) == 3:
            break
        threading.Event().wait(0.1)

    assert len(db._bg_conns) == 3
    assert len(acquired) == 3
    db._close_pooled_conn()
    release.set()
    for t in threads:
        t.join()

    assert db._bg_conns == []
    assert db._pooled_conn is None
    assert results == [True, True, True]
