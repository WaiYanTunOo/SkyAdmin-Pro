from __future__ import annotations


class BackupMixinMixin0:
    def _refresh_backup_banner(self) -> None:
        from datetime import date as _date

        from skyadmin_pro.config import SETTING_LAST_ENCRYPTED_BACKUP

        raw = self.app.db.get_setting(SETTING_LAST_ENCRYPTED_BACKUP)
        if not raw:
            self.backup_banner.configure(
                text="⚠ You have NEVER created an encrypted backup — your data "
                "has no off-machine copy. Create one now (2 minutes).",
                text_color=("#b45309", "#fbbf24"),
            )
            return
        try:
            last = _date.fromisoformat(str(raw)[:10])
            days = (_date.today() - last).days
        except ValueError:
            days = 999
        if days >= 7:
            self.backup_banner.configure(
                text=f"⚠ Last encrypted backup was {days} day(s) ago — create a fresh one.",
                text_color=("#b45309", "#fbbf24"),
            )
        else:
            self.backup_banner.configure(
                text=f"✓ Last encrypted backup: {last.isoformat()} ({days} day(s) ago).",
                text_color=("#15803d", "#4ade80"),
            )

    def _toggle_auto_backup(self) -> None:
        from skyadmin_pro.services.auto_backup import (
            SETTING_AUTO_BACKUP_ENABLED,
            SETTING_AUTO_BACKUP_INTERVAL,
        )

        enabled = self._auto_backup_enabled_var.get()
        interval = self._auto_backup_interval_var.get()
        self.app.db.set_setting(SETTING_AUTO_BACKUP_ENABLED, enabled)
        self.app.db.set_setting(SETTING_AUTO_BACKUP_INTERVAL, interval)
        scheduler = getattr(self.app, "_auto_backup", None)
        nudge = getattr(scheduler, "nudge", None)
        if callable(nudge):
            try:
                nudge()
            except Exception:
                pass
        if enabled == "1":
            self.feedback.info(f"Auto-backup enabled ({interval}).")
            self.app.set_status(f"Auto-backup on ({interval}) — schedule updated")
        else:
            self.feedback.info("Auto-backup disabled.")
            self.app.set_status("Auto-backup disabled")

    def _open_auto_backups_folder(self) -> None:
        """Create AutoBackups/ if missing and open it for restore/browse."""
        from skyadmin_pro.services.auto_backup import auto_backups_dir

        folder = auto_backups_dir(self.app.paths.root)
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.feedback.error(f"Could not create AutoBackups folder: {exc}")
            return
        self._open_path(folder)
        self.app.set_status(f"Opened AutoBackups: {folder}")
