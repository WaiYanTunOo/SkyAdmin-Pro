"""Settings view mixins."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from skyadmin_pro.config import (
    CHECKLIST_TEMPLATES,
    DEFAULT_COLOR_THEME,
    DEFAULT_PORTAL_URL,
    MOBILE_VIEWER_URL,
    OWNER_EMAIL,
    PRICING_DEFAULT_SERVICE,
    SERVICE_TYPES,
    SETTING_APPEARANCE_MODE,
    SETTING_COLOR_THEME,
    SETTING_PORTAL_URL,
    SETTING_WORKSPACE_CUSTOM,
    SETTING_WORKSPACE_ROOT,
    pricing_uses_transaction_ranges,
)
from skyadmin_pro.paths import WorkspacePaths
from skyadmin_pro.services.data_hygiene import run_data_hygiene
from skyadmin_pro.services.file_ops import open_in_file_manager
from skyadmin_pro.services.workflow import normalize_portal_url, repair_client_workspaces
from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import FeedbackLabel, bind_wrap_label, make_modal, themed_entry


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

    def _backup_encrypted(self) -> None:
        dest = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Save Encrypted Backup",
            defaultextension=".skybackup",
            initialfile=f"SkyAdminPro_Backup_{__import__('datetime').date.today().isoformat()}.skybackup",
            filetypes=[("SkyAdmin Backup", "*.skybackup"), ("All files", "*.*")],
        )
        if not dest:
            return
        self.feedback.info("Creating encrypted backup… please wait.")
        self.configure(cursor="watch")
        self.update_idletasks()
        import threading

        def _worker():
            err = None
            try:
                from skyadmin_pro.services.crypto import create_encrypted_backup

                create_encrypted_backup(self.app.paths.root, self.app.db.db_file, Path(dest))
            except Exception as exc:
                err = str(exc)

            def _done():
                if not self.winfo_exists():
                    return
                self.configure(cursor="")
                if err:
                    self.feedback.error(f"Backup failed: {err}")
                else:
                    from skyadmin_pro.services.crypto import format_byte_size

                    size = format_byte_size(Path(dest).stat().st_size)
                    self.feedback.success(f"Encrypted backup saved: {Path(dest).name} ({size})")
                    from datetime import date as _d

                    from skyadmin_pro.config import SETTING_LAST_ENCRYPTED_BACKUP

                    self.app.db.set_setting(SETTING_LAST_ENCRYPTED_BACKUP, _d.today().isoformat())
                    self._refresh_backup_banner()
                    self.app.set_status(f"Backup saved to {dest}")

            try:
                self.after(0, _done)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _restore_encrypted(self) -> None:
        src = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Restore Encrypted Backup",
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
        self.update_idletasks()
        import threading

        def _worker():
            err = None
            safety_path = None
            summary = None
            try:
                from datetime import datetime as _dt

                from skyadmin_pro.services.crypto import (
                    create_encrypted_backup,
                    restore_encrypted_backup,
                )

                backup_dir = self.app.db.db_file.parent / "backups"
                backup_dir.mkdir(parents=True, exist_ok=True)
                stamp = _dt.now().strftime("%Y%m%d_%H%M%S")
                safety_path = backup_dir / f"pre_restore_{stamp}.skybackup"
                create_encrypted_backup(self.app.paths.root, self.app.db.db_file, safety_path)
                summary = restore_encrypted_backup(src_path, self.app.paths.root, self.app.db.db_file)
            except Exception as exc:
                err = str(exc)

            def _done():
                if not self.winfo_exists():
                    return
                self.configure(cursor="")
                if err:
                    self.feedback.error(f"Restore failed: {err}")
                else:
                    from skyadmin_pro.services.crypto import format_byte_size

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
                        "Close and reopen SkyAdmin Pro to load the restored data.",
                        parent=self.winfo_toplevel(),
                    )

            try:
                self.after(0, _done)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

