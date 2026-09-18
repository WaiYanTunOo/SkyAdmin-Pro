from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.widgets import SectionCard, bind_wrap_label


class SettingsViewMixin8:
    def _SettingsView_build_license_tab_status_p1(self, scroll, row):
        status = SectionCard(
            scroll,
            title="License & sync",
            subtitle=(
                "Keys are issued in the browser admin. This screen only activates this PC. "
                "Upload this PC is a backup of this machine, not a shared office database. "
                "A second PC uses Data & backup → encrypted backup (.skybackup)."
            ),
        )
        status.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        body = status.body
        body.grid_columnconfigure(0, weight=1)

        self.license_label = ctk.CTkLabel(body, text="License: checking…", anchor="w", text_color=TEXT_MUTED)
        self.license_label.grid(row=0, column=0, sticky="ew")
        bind_wrap_label(self.license_label, body, pad=24)

        self.daily_sync_label = ctk.CTkLabel(
            body,
            text="",
            anchor="w",
            text_color=TEXT_MUTED,
            justify="left",
        )
        self.daily_sync_label.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        bind_wrap_label(self.daily_sync_label, body, pad=24)

        self.data_sync_label = ctk.CTkLabel(
            body,
            text="",
            anchor="w",
            text_color=TEXT_MUTED,
            justify="left",
        )
        self.data_sync_label.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        bind_wrap_label(self.data_sync_label, body, pad=24)

        sync_btns = ctk.CTkFrame(body, fg_color="transparent")
        sync_btns.grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.sync_now_btn = ctk.CTkButton(sync_btns, text="Upload this PC", width=130, command=self._sync_now)
        self.sync_now_btn.pack(side="left", padx=(0, 8))
        self.conflicts_btn = ctk.CTkButton(
            sync_btns,
            text="Conflicts",
            width=100,
            fg_color="transparent",
            border_width=1,
            state="disabled",
            command=self._open_sync_conflicts,
        )
        self.conflicts_btn.pack(side="left", padx=(0, 8))
        return body, sync_btns
