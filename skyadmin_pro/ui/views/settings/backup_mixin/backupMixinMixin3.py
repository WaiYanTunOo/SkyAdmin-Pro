from __future__ import annotations

from tkinter import messagebox


class BackupMixinMixin3:
    def _BackupMixin_restore_encrypted_p3(self, run_background, work):
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

        def _on_error(err) -> None:
            try:
                self.app.db.end_restore_lockout()
            except Exception:
                self.app.db._restore_lockout = False
            self.feedback.error(f"Restore failed: {err}")

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
            on_error=_on_error,
            finally_fn=_enable_backup_buttons,
            feedback=self.feedback,
        )
