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
                "Sign in with Google — PDFs stay in YOUR Drive (not vendor storage). "
                "Requires the Files-on-Drive license SKU."
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
            text=("Connected." if connected else "Not connected — click Sign in with Google.")
            if unlocked
            else "Locked — license does not include Drive files.",
            anchor="w",
            text_color=TEXT_MUTED,
        )
        self._drive_status.grid(row=0, column=0, sticky="ew")
        bind_wrap_label(self._drive_status, body, pad=24)
        next_row = self._SettingsView_build_drive_connect_row(body, unlocked=unlocked, start_row=1)
        next_row = self._SettingsView_build_drive_oauth_fields(body, unlocked=unlocked, start_row=next_row)
        self._drive_backfill_btn = ctk.CTkButton(
            body,
            text="Upload existing files to Drive",
            width=220,
            state="normal" if unlocked else "disabled",
            command=self._backfill_drive_files,
        )
        self._drive_backfill_btn.grid(row=next_row, column=0, sticky="w", pady=(8, 0))
        self._drive_relink_btn = ctk.CTkButton(
            body,
            text="Relink local files → Drive",
            width=220,
            state="normal" if unlocked else "disabled",
            command=self._relink_and_backfill_drive_files,
        )
        self._drive_relink_btn.grid(row=next_row + 1, column=0, sticky="w", pady=(8, 0))
        self._drive_clear_btn = ctk.CTkButton(
            body,
            text="Clear broken file links",
            width=220,
            fg_color="transparent",
            border_width=1,
            state="normal" if unlocked else "disabled",
            command=self._clear_broken_document_files,
        )
        self._drive_clear_btn.grid(row=next_row + 2, column=0, sticky="w", pady=(8, 0))
        self._drive_portable_btn = ctk.CTkButton(
            body,
            text="Make paths portable",
            width=220,
            fg_color="transparent",
            border_width=1,
            command=self._normalize_portable_paths,
        )
        self._drive_portable_btn.grid(row=next_row + 3, column=0, sticky="w", pady=(8, 0))
        return row + 1

    def _SettingsView_build_drive_connect_row(self, body, *, unlocked: bool, start_row: int) -> int:
        btns = ctk.CTkFrame(body, fg_color="transparent")
        btns.grid(row=start_row, column=0, sticky="w", pady=(8, 0))
        state = "normal" if unlocked else "disabled"
        self._drive_connect_btn = ctk.CTkButton(
            btns, text="Sign in with Google", width=180, state=state, command=self._connect_google_drive
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
        return start_row + 1
