from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.widgets import bind_wrap_label


class SettingsViewMixin13:
    def _SettingsView_build_data_tab_backup_p2(self, auto_frame, backup_body, retention_help_text):
        ctk.CTkOptionMenu(
            auto_frame,
            variable=self._auto_backup_interval_var,
            values=["daily", "weekly", "off"],
            width=100,
            command=lambda _: self._toggle_auto_backup(),
        ).pack(side="left", padx=(0, 12))
        self.auto_backup_retention_label = ctk.CTkLabel(
            backup_body,
            text=retention_help_text(),
            anchor="w",
            justify="left",
            text_color=TEXT_MUTED,
        )
        self.auto_backup_retention_label.grid(row=5, column=0, sticky="ew", pady=(6, 0))
        bind_wrap_label(self.auto_backup_retention_label, backup_body, pad=24)
