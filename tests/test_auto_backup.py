"""Tests for scheduled auto-backup — prune policy, banner key, toast."""

from __future__ import annotations

from datetime import datetime, timedelta

from skyadmin_pro.services.auto_backup import (
    AUTO_BACKUP_KEEP,
    SETTING_AUTO_BACKUP_ENABLED,
    SETTING_AUTO_BACKUP_INTERVAL,
    SETTING_AUTO_BACKUP_LAST_RUN,
    AutoBackupScheduler,
    prune_old_backups,
    should_run_backup,
)


class _FakeDb:
    def __init__(self) -> None:
        self.settings: dict[str, str] = {}
        self.db_file = "/fake/skyadmin.db"

    def get_setting(self, key: str, default: str | None = None):
        return self.settings.get(key, default)

    def set_setting(self, key: str, value: str) -> None:
        self.settings[key] = value


class _FakePaths:
    def __init__(self, root) -> None:
        self.root = root


class _FakeApp:
    def __init__(self, db, root) -> None:
        self.db = db
        self.paths = _FakePaths(root)
        self.status_messages: list[str] = []
        self._after_calls: list = []

    def after(self, ms, func):
        self._after_calls.append((ms, func))
        return "timer-1"

    def after_cancel(self, _timer_id):
        pass

    def set_status(self, message: str) -> None:
        self.status_messages.append(message)


def _make_backups(backup_dir, count: int):
    backup_dir.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (backup_dir / f"SkyAdminPro_AutoBackup_2026-01-{i + 1:02d}.skybackup").write_bytes(b"x")


class TestPruneOldBackups:
    def test_keeps_newest_seven(self, tmp_path):
        backup_dir = tmp_path / "AutoBackups"
        _make_backups(backup_dir, 10)
        removed = prune_old_backups(backup_dir)
        assert removed == 3
        remaining = sorted(p.name for p in backup_dir.glob("*.skybackup"))
        assert len(remaining) == AUTO_BACKUP_KEEP
        assert remaining[0].endswith("2026-01-04.skybackup")

    def test_under_limit_prunes_nothing(self, tmp_path):
        backup_dir = tmp_path / "AutoBackups"
        _make_backups(backup_dir, 3)
        assert prune_old_backups(backup_dir) == 0
        assert len(list(backup_dir.glob("*.skybackup"))) == 3

    def test_missing_dir_returns_zero(self, tmp_path):
        assert prune_old_backups(tmp_path / "nope") == 0


class TestShouldRunBackup:
    def test_off_never_runs(self):
        assert should_run_backup(None, "off", None) is False

    def test_first_run_always_runs(self):
        assert should_run_backup(None, "daily", None) is True

    def test_daily_elapsed(self):
        last = (datetime.now() - timedelta(hours=25)).isoformat()
        assert should_run_backup(None, "daily", last) is True

    def test_daily_too_soon(self):
        last = (datetime.now() - timedelta(hours=1)).isoformat()
        assert should_run_backup(None, "daily", last) is False


class TestSchedulerCheck:
    def test_success_sets_banner_key_last_run_and_toast(self, tmp_path, monkeypatch):
        from skyadmin_pro.services import auto_backup as ab

        monkeypatch.setattr(ab, "run_auto_backup", lambda *a: tmp_path / "b.skybackup")
        db = _FakeDb()
        db.set_setting(SETTING_AUTO_BACKUP_ENABLED, "1")
        db.set_setting(SETTING_AUTO_BACKUP_INTERVAL, "daily")
        app = _FakeApp(db, tmp_path)
        AutoBackupScheduler(app)._check()

        assert SETTING_AUTO_BACKUP_LAST_RUN in db.settings
        assert db.settings.get("last_encrypted_backup") is not None
        assert any("Auto-backup completed" in m for m in app.status_messages)

    def test_disabled_does_nothing(self, tmp_path, monkeypatch):
        from skyadmin_pro.services import auto_backup as ab

        called = []
        monkeypatch.setattr(ab, "run_auto_backup", lambda *a: called.append(a) or tmp_path)
        db = _FakeDb()
        app = _FakeApp(db, tmp_path)
        AutoBackupScheduler(app)._check()
        assert called == []
        assert app.status_messages == []
