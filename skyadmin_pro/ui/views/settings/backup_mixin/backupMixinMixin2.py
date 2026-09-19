from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox


class BackupMixinMixin2:
    def _restore_encrypted(self) -> None:
        src = self._BackupMixin_restore_encrypted_p1()
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
        preview = self._BackupMixin_restore_encrypted_p2(format_byte_size, info, src_path)
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

            db = self.app.db
            ok = False
            try:
                backup_dir = db.db_file.parent / "backups"
                backup_dir.mkdir(parents=True, exist_ok=True)
                stamp = _dt.now().strftime("%Y%m%d_%H%M%S")
                safety_path = backup_dir / f"pre_restore_{stamp}.skybackup"
                # Safety snapshot while the live DB may still be open — do this
                # BEFORE lockout so we never reopen the live file for replace.
                create_encrypted_backup(self.app.paths.root, db.db_file, safety_path)
                try:
                    db.begin_restore_lockout()
                except Exception:
                    try:
                        db.shutdown()
                    except Exception:
                        pass
                    db._restore_lockout = True
                    db._close_pooled_conn()
                summary = restore_encrypted_backup(src_path, self.app.paths.root, db.db_file)
                ok = True
                return safety_path, summary
            finally:
                if not ok:
                    try:
                        db.end_restore_lockout()
                    except Exception:
                        db._restore_lockout = False

        self._BackupMixin_restore_encrypted_p3(run_background, work)

    def _BackupMixin_restore_encrypted_p1(self):
        from skyadmin_pro.services.auto_backup import auto_backups_dir

        auto_dir = auto_backups_dir(self.app.paths.root, self.app.db)
        initial = str(auto_dir) if auto_dir.is_dir() else None
        src = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Restore Encrypted Backup",
            initialdir=initial,
            filetypes=[("SkyAdmin Backup", "*.skybackup"), ("All files", "*.*")],
        )
        return src

    def _BackupMixin_restore_encrypted_p2(self, format_byte_size, info, src_path):
        preview = (
            f"Backup file: {src_path.name}\n"
            f"Encrypted size: {format_byte_size(info.encrypted_bytes)}\n"
            f"Database: {format_byte_size(info.database_bytes)}\n"
            f"Workspace: {info.workspace_file_count} file(s), {format_byte_size(info.workspace_bytes)}\n\n"
            "Your current database and workspace will be overwritten.\n"
            "A safety copy of the current data is saved automatically before restore.\n\n"
            "Continue?"
        )
        return preview
