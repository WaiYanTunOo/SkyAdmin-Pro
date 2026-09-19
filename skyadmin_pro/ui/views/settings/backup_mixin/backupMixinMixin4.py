from __future__ import annotations

from pathlib import Path
from tkinter import filedialog


class BackupMixinMixin4:
    def _browse_backup_destination(self) -> None:
        from skyadmin_pro.services.auto_backup import auto_backups_dir

        initial = auto_backups_dir(self.app.paths.root, self.app.db)
        chosen = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            title="Choose backup destination folder",
            initialdir=str(initial) if initial.is_dir() else str(self.app.paths.root),
        )
        if not chosen:
            return
        self._backup_dest_var.set(chosen)
        self._save_backup_destination()

    def _save_backup_destination(self) -> None:
        from skyadmin_pro.services.auto_backup import SETTING_BACKUP_DESTINATION, auto_backups_dir

        raw = (self._backup_dest_var.get() or "").strip()
        if not raw:
            self.app.db.set_setting(SETTING_BACKUP_DESTINATION, "")
            resolved = auto_backups_dir(self.app.paths.root, self.app.db)
            self._backup_dest_var.set(str(resolved))
            self.feedback.info(f"Backup folder reset to default: {resolved}")
            return
        path = Path(raw)
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.feedback.error(f"Could not use backup folder: {exc}")
            return
        if not path.is_dir():
            self.feedback.error("Backup destination must be an existing folder.")
            return
        self.app.db.set_setting(SETTING_BACKUP_DESTINATION, str(path.resolve()))
        self._backup_dest_var.set(str(path.resolve()))
        self.feedback.success(f"Backup folder saved: {path}")
        self.app.set_status(f"Backup folder: {path}")
