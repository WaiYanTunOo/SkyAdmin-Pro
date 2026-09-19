from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.widgets import SectionCard, bind_wrap_label


class SettingsViewMixin14:
    def _SettingsView_build_drive_card(self, scroll, row: int) -> int:
        from skyadmin_pro.services.drive import (
            SETTING_DRIVE_FILES_ENABLED,
            drive_connect_unlocked,
            load_refresh_token,
        )

        card = SectionCard(
            scroll,
            title="Google Drive files",
            subtitle=(
                "Store PDFs in YOUR Google Drive (not vendor storage). " "Requires the Files-on-Drive license SKU."
            ),
        )
        card.grid(row=row, column=0, sticky="ew", pady=(12, 0))
        body = card.body
        unlocked = drive_connect_unlocked(self.app.db)
        connected = bool(load_refresh_token(self.app.db))
        self._drive_enabled_var = ctk.StringVar(
            value="1" if (self.app.db.get_setting(SETTING_DRIVE_FILES_ENABLED) or "") == "1" else "0"
        )
        self._drive_status = ctk.CTkLabel(
            body,
            text=("Connected." if connected else "Not connected.")
            if unlocked
            else "Locked — license does not include Drive files.",
            anchor="w",
            text_color=TEXT_MUTED,
        )
        self._drive_status.grid(row=0, column=0, sticky="ew")
        bind_wrap_label(self._drive_status, body, pad=24)
        btns = ctk.CTkFrame(body, fg_color="transparent")
        btns.grid(row=1, column=0, sticky="w", pady=(8, 0))
        state = "normal" if unlocked else "disabled"
        self._drive_connect_btn = ctk.CTkButton(
            btns, text="Connect Google Drive", width=180, state=state, command=self._connect_google_drive
        )
        self._drive_connect_btn.pack(side="left", padx=(0, 8))
        self._drive_disconnect_btn = ctk.CTkButton(
            btns,
            text="Disconnect",
            width=110,
            fg_color="transparent",
            border_width=1,
            state=state,
            command=self._disconnect_google_drive,
        )
        self._drive_disconnect_btn.pack(side="left", padx=(0, 8))
        ctk.CTkSwitch(
            btns,
            text="Prefer Drive for new files",
            variable=self._drive_enabled_var,
            onvalue="1",
            offvalue="0",
            state=state,
            command=self._toggle_drive_files_pref,
        ).pack(side="left")
        self._drive_backfill_btn = ctk.CTkButton(
            body,
            text="Upload existing files to Drive",
            width=220,
            state=state,
            command=self._backfill_drive_files,
        )
        self._drive_backfill_btn.grid(row=2, column=0, sticky="w", pady=(8, 0))
        return row + 1
