from __future__ import annotations

from tkinter import messagebox


class LicenseMixinMixin3:
    def _begin_license_background(self, action: str, status: str) -> None:
        """Disable sync/update controls while a background license task runs."""
        self._license_bg_action = action
        self.configure(cursor="watch")
        self.feedback.info(status)
        sync_btn = getattr(self, "sync_now_btn", None)
        upd_btn = getattr(self, "check_updates_btn", None)
        if sync_btn is not None:
            sync_btn.configure(
                state="disabled",
                text="Syncing…" if action == "sync" else sync_btn.cget("text"),
            )
        if upd_btn is not None:
            upd_btn.configure(
                state="disabled",
                text="Checking…" if action == "updates" else upd_btn.cget("text"),
            )

    def _end_license_background(self) -> None:
        self.configure(cursor="")
        sync_btn = getattr(self, "sync_now_btn", None)
        upd_btn = getattr(self, "check_updates_btn", None)
        if sync_btn is not None:
            sync_btn.configure(state="normal", text="Upload this PC")
        if upd_btn is not None:
            upd_btn.configure(state="normal", text="Check updates")

    def _format_data_sync_status(self) -> str:
        from skyadmin_pro.config import SETTING_SYNC_LAST_PULL
        from skyadmin_pro.services.data_sync import is_data_sync_enabled

        if not is_data_sync_enabled(self.app.db):
            return "Cloud data sync: off (use encrypted backup for a second PC)"
        last = (self.app.db.get_setting(SETTING_SYNC_LAST_PULL) or "").strip()
        conflicts = self.app.db.count_sync_conflicts()
        parts: list[str] = []
        if last:
            display = last.replace("T", " ")[:19]
            parts.append(f"Last data sync: {display}")
        else:
            parts.append("Data sync: never")
        if conflicts:
            parts.append(f"{conflicts} sync conflict(s) logged")
        return " · ".join(parts)

    def _run_integrity_check(self) -> None:
        ok = self.app.db.quick_check()
        self._refresh_integrity_banner()
        if ok:
            messagebox.showinfo(
                "Database integrity",
                "✓ quick_check passed — your local database looks healthy.",
                parent=self.winfo_toplevel(),
            )
            self.feedback.success("Database integrity check passed.")
            return
        messagebox.showwarning(
            "Database integrity",
            "✗ Integrity check failed.\n\n"
            "Restore from an encrypted backup (.skybackup) or a daily snapshot in "
            f"{self.app.db.db_file.parent / 'backups'} if data looks wrong.",
            parent=self.winfo_toplevel(),
        )
        self.feedback.error("Database integrity check failed — see dialog.")

    def _refresh_integrity_banner(self) -> None:
        banner = getattr(self, "integrity_banner", None)
        if banner is None:
            return
        try:
            ok = self.app.db.quick_check()
        except Exception:
            banner.configure(text="⚠ Database integrity check could not run — contact support if data looks wrong.")
            banner.grid()
            return
        if ok:
            banner.configure(text="")
            banner.grid_remove()
        else:
            banner.configure(
                text=(
                    "⚠ Database integrity check failed. Restore from an encrypted backup "
                    "or a daily snapshot before continuing heavy work."
                )
            )
            banner.grid()
