"""restore_backup must close the pooled connection before overwriting the DB file."""

from __future__ import annotations

import shutil
from pathlib import Path

from skyadmin_pro.db.database import Database


def test_restore_backup_closes_pool_before_overwrite(tmp_path: Path, monkeypatch):
    live = tmp_path / "live.db"
    db = Database(live)
    with db.connection() as conn:
        conn.execute("SELECT 1").fetchone()

    backup_path = tmp_path / "backup.db"
    db.backup_to(backup_path)
    assert backup_path.exists()

    order: list[str] = []
    real_close = db._close_pooled_conn
    real_copy = shutil.copy2

    def tracking_close():
        order.append("close")
        return real_close()

    def tracking_copy(src, dst, *a, **k):
        order.append("copy")
        assert "close" in order, "pool must be closed before copy2"
        return real_copy(src, dst, *a, **k)

    monkeypatch.setattr(db, "_close_pooled_conn", tracking_close)
    monkeypatch.setattr(shutil, "copy2", tracking_copy)

    assert db.restore_backup(backup_path) is True
    assert order[:2] == ["close", "copy"], f"expected close before copy, got {order}"
