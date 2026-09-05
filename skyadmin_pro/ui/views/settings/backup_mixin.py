"""Settings view mixins."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox


class BackupMixin:
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

    def _backup_encrypted(self) -> None:
        dest = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Save Encrypted Backup",
            defaultextension=".skybackup",
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

    def _restore_encrypted(self) -> None:
        from skyadmin_pro.services.auto_backup import auto_backups_dir

        auto_dir = auto_backups_dir(self.app.paths.root)
        initial = str(auto_dir) if auto_dir.is_dir() else None
        src = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Restore Encrypted Backup",
            initialdir=initial,
            filetypes=[("SkyAdmin Backup", "*.skybackup"), ("All files", "*.*")],
        )
        if not src:
            return
        src_path = Path(src)
        self.feedback.info("Reading backup…")
        self.configure(cursor="watch")
        self.update_idletasks()
        try:
            from skyadmin_pro.services.crypto import format_byte_size, inspect_encrypted_backup

            info = inspect_encrypted_backup(src_path)
        except ValueError as exc:
            self.configure(cursor="")
            self.feedback.error(str(exc))
            return
        finally:
            self.configure(cursor="")

        if not info.has_database:
            messagebox.showerror(
                "Invalid backup",
                "This backup does not contain skyadmin_pro.db and cannot be restored.",
                parent=self.winfo_toplevel(),
            )
            return

        preview = (
            f"Backup file: {src_path.name}\n"
            f"Encrypted size: {format_byte_size(info.encrypted_bytes)}\n"
            f"Database: {format_byte_size(info.database_bytes)}\n"
            f"Workspace: {info.workspace_file_count} file(s), {format_byte_size(info.workspace_bytes)}\n\n"
            "Your current database and workspace will be overwritten.\n"
            "A safety copy of the current data is saved automatically before restore.\n\n"
            "Continue?"
        )
        if not messagebox.askyesno(
            "Restore backup",
            preview,
            parent=self.winfo_toplevel(),
        ):
            return
        self.feedback.info("Restoring encrypted backup… please wait.")
        self.configure(cursor="watch")
        for btn in (getattr(self, "backup_action_btn", None), getattr(self, "restore_backup_btn", None)):
            if btn is not None:
                btn.configure(state="disabled")
        self.update_idletasks()
        from skyadmin_pro.ui.async_ui import run_background

        def work() -> None:
            from datetime import datetime as _dt

            from skyadmin_pro.services.crypto import (
                create_encrypted_backup,
                restore_encrypted_backup,
            )

            try:
                self.app.db.shutdown()
            except Exception:
                pass

            backup_dir = self.app.db.db_file.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = _dt.now().strftime("%Y%m%d_%H%M%S")
            safety_path = backup_dir / f"pre_restore_{stamp}.skybackup"
            create_encrypted_backup(self.app.paths.root, self.app.db.db_file, safety_path)
            summary = restore_encrypted_backup(src_path, self.app.paths.root, self.app.db.db_file)
            return safety_path, summary

        def on_success(result) -> None:
            from skyadmin_pro.services.crypto import format_byte_size

            safety_path, summary = result
            restored = (
                f"Database: {format_byte_size(summary.database_bytes)}\n"
                f"Workspace: {summary.workspace_files_restored} file(s), "
                f"{format_byte_size(summary.workspace_bytes)}"
            )
            safety = f"\n\nSafety backup:\n{safety_path}" if safety_path is not None else ""
            self.feedback.success("Restore complete — please restart the app.")
            self.app.set_status("Restore complete — restart required")
            messagebox.showinfo(
                "Restore complete",
                f"Backup restored successfully.\n\n{restored}{safety}\n\n"
                "SkyAdmin Pro will close now. Reopen it to load the restored data.",
                parent=self.winfo_toplevel(),
            )
            try:
                self.app.db.shutdown()
            except Exception:
                pass
            root = self.winfo_toplevel()
            try:
                root.destroy()
            except Exception:
                pass

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
            on_error=lambda err: self.feedback.error(f"Restore failed: {err}"),
            finally_fn=_enable_backup_buttons,
            feedback=self.feedback,
        )
