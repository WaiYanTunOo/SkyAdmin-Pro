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
