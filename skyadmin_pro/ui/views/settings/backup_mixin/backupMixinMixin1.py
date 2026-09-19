from __future__ import annotations

from datetime import date
from pathlib import Path
from tkinter import filedialog


class BackupMixinMixin1:
    def _backup_encrypted(self) -> None:
        from skyadmin_pro.services.auto_backup import auto_backups_dir

        initial = auto_backups_dir(self.app.paths.root, self.app.db)
        try:
            initial.mkdir(parents=True, exist_ok=True)
        except OSError:
            initial = self.app.paths.root
        dest = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Save Encrypted Backup",
            defaultextension=".skybackup",
            initialdir=str(initial) if Path(initial).is_dir() else str(self.app.paths.root),
            initialfile=f"SkyAdminPro_Backup_{date.today().isoformat()}.skybackup",
            filetypes=[("SkyAdmin Backup", "*.skybackup"), ("All files", "*.*")],
        )
        if not dest:
            return
        self.feedback.info("Creating encrypted backup… please wait.")
        self.configure(cursor="watch")
        for btn in (getattr(self, "backup_action_btn", None), getattr(self, "restore_backup_btn", None)):
            if btn is not None:
                btn.configure(state="disabled")
        self.update_idletasks()
        from skyadmin_pro.ui.async_ui import run_background

        dest_path = Path(dest)

        def work() -> Path:
            from skyadmin_pro.services.crypto import create_encrypted_backup

            create_encrypted_backup(self.app.paths.root, self.app.db.db_file, dest_path)
            return dest_path

        def on_success(saved: Path) -> None:
            from skyadmin_pro.services.crypto import format_byte_size

            size = format_byte_size(saved.stat().st_size)
            self.feedback.success(f"Encrypted backup saved: {saved.name} ({size})")
            from datetime import date as _d

            from skyadmin_pro.config import SETTING_LAST_ENCRYPTED_BACKUP

            self.app.db.set_setting(SETTING_LAST_ENCRYPTED_BACKUP, _d.today().isoformat())
            self._refresh_backup_banner()
            self.app.set_status(f"Backup saved to {dest}")

        def _enable_backup_buttons() -> None:
            self.configure(cursor="")
            if getattr(self, "backup_action_btn", None) is not None:
                self.backup_action_btn.configure(state="normal")
            if getattr(self, "restore_backup_btn", None) is not None:
                self.restore_backup_btn.configure(state="normal")

        run_background(
            self,
            work=work,
            on_success=on_success,
            on_error=lambda err: self.feedback.error(f"Backup failed: {err}"),
            finally_fn=_enable_backup_buttons,
            feedback=self.feedback,
        )
