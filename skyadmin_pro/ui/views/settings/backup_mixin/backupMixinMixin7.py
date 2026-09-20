from __future__ import annotations


class BackupMixinMixin7:
    def _persist_drive_oauth_from_entries(self) -> None:
        from skyadmin_pro.services.drive.keys import SETTING_DRIVE_CLIENT_ID
        from skyadmin_pro.services.drive.tokens import save_client_config

        id_entry = getattr(self, "_drive_client_id_entry", None)
        secret_entry = getattr(self, "_drive_client_secret_entry", None)
        if id_entry is None:
            return
        client_id = (id_entry.get() or "").strip()
        client_secret = (secret_entry.get() or "").strip() if secret_entry is not None else ""
        if not client_id and not client_secret:
            return
        if not client_id:
            client_id = (self.app.db.get_setting(SETTING_DRIVE_CLIENT_ID) or "").strip()
        save_client_config(self.app.db, client_id, client_secret)

    def _save_drive_oauth_client(self) -> None:
        from skyadmin_pro.services.drive import drive_connect_unlocked
        from skyadmin_pro.services.drive.tokens import resolve_client_id, resolve_client_secret

        if not drive_connect_unlocked(self.app.db):
            self.feedback.error("Drive files are not enabled on this license.")
            return
        self._persist_drive_oauth_from_entries()
        if not resolve_client_id(self.app.db) or not resolve_client_secret(self.app.db):
            self.feedback.error("Enter both OAuth client ID and client secret.")
            return
        secret_entry = getattr(self, "_drive_client_secret_entry", None)
        if secret_entry is not None and (secret_entry.get() or "").strip():
            secret_entry.delete(0, "end")
            secret_entry.configure(placeholder_text="Client secret (saved)")
        self.feedback.success("OAuth client saved. Click Sign in with Google next.")
