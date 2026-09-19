from __future__ import annotations


class BackupMixinMixin5:
    def _connect_google_drive(self) -> None:
        from skyadmin_pro.services.drive import NotConfiguredError, connect_google_drive, drive_connect_unlocked

        if not drive_connect_unlocked(self.app.db):
            self.feedback.error("Drive files are not enabled on this license.")
            return
        try:
            msg = connect_google_drive(self.app.db)
            self.feedback.success(msg)
            if getattr(self, "_drive_status", None) is not None:
                self._drive_status.configure(text="Connected.")
        except NotConfiguredError as exc:
            self.feedback.error(str(exc))
        except Exception as exc:
            self.feedback.error(f"Drive connect failed: {exc}")

    def _disconnect_google_drive(self) -> None:
        from skyadmin_pro.services.drive import clear_drive_tokens

        clear_drive_tokens(self.app.db)
        self.feedback.info("Google Drive disconnected.")
        if getattr(self, "_drive_status", None) is not None:
            self._drive_status.configure(text="Not connected.")

    def _toggle_drive_files_pref(self) -> None:
        from skyadmin_pro.services.drive import SETTING_DRIVE_FILES_ENABLED, drive_connect_unlocked

        if not drive_connect_unlocked(self.app.db):
            self._drive_enabled_var.set("0")
            self.feedback.error("Drive files are not enabled on this license.")
            return
        val = self._drive_enabled_var.get()
        self.app.db.set_setting(SETTING_DRIVE_FILES_ENABLED, val)
        self.feedback.info("Drive preference saved." if val == "1" else "Drive preference off — local files only.")
