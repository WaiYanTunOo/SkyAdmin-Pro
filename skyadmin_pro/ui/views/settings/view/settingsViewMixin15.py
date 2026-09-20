from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED


class SettingsViewMixin15:
    def _SettingsView_build_drive_oauth_fields(self, body, *, unlocked: bool, start_row: int) -> int:
        """Collapsed Advanced block for custom OAuth Desktop client override."""
        from skyadmin_pro.services.drive.keys import SETTING_DRIVE_CLIENT_ID, SETTING_DRIVE_CLIENT_SECRET
        from skyadmin_pro.services.drive.tokens import resolve_client_id

        state = "normal" if unlocked else "disabled"
        self._drive_adv_var = ctk.StringVar(value="0")
        adv_btn = ctk.CTkCheckBox(
            body,
            text="Advanced — custom OAuth app",
            variable=self._drive_adv_var,
            onvalue="1",
            offvalue="0",
            state=state,
            command=self._toggle_drive_oauth_advanced,
        )
        adv_btn.grid(row=start_row, column=0, sticky="w", pady=(10, 0))
        self._drive_oauth_adv = ctk.CTkFrame(body, fg_color="transparent")
        self._drive_oauth_adv.grid(row=start_row + 1, column=0, sticky="ew")
        ctk.CTkLabel(
            self._drive_oauth_adv,
            text="Desktop clients need Client secret here (encrypted locally). Env GOOGLE_OAUTH_* also wins.",
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        self._drive_client_id_entry = ctk.CTkEntry(
            self._drive_oauth_adv, placeholder_text="OAuth client ID", width=420, state=state
        )
        self._drive_client_id_entry.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        stored_id = (self.app.db.get_setting(SETTING_DRIVE_CLIENT_ID) or "").strip()
        if stored_id and unlocked:
            self._drive_client_id_entry.insert(0, stored_id)
        secret_row = ctk.CTkFrame(self._drive_oauth_adv, fg_color="transparent")
        secret_row.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        has_secret = bool((self.app.db.get_setting(SETTING_DRIVE_CLIENT_SECRET) or "").strip())
        self._drive_client_secret_entry = ctk.CTkEntry(
            secret_row,
            placeholder_text=("Client secret (saved)" if has_secret else "OAuth client secret (required for Desktop)"),
            show="•",
            width=320,
            state=state,
        )
        self._drive_client_secret_entry.pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            secret_row, text="Save client", width=110, state=state, command=self._save_drive_oauth_client
        ).pack(side="left")
        has_id = bool(resolve_client_id(self.app.db))
        if stored_id or not has_id:
            self._drive_adv_var.set("1")
        else:
            self._drive_oauth_adv.grid_remove()
        return start_row + 2

    def _toggle_drive_oauth_advanced(self) -> None:
        frame = getattr(self, "_drive_oauth_adv", None)
        if frame is None:
            return
        if self._drive_adv_var.get() == "1":
            frame.grid()
        else:
            frame.grid_remove()
