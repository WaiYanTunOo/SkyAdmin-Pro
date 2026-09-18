from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.widgets import SectionCard, bind_wrap_label


class SettingsViewMixin11:
    def _SettingsView_build_data_tab_backup_p1(self, scroll, row):
        backup = SectionCard(
            scroll,
            title="Encrypted data backup",
            subtitle=(
                "Create a .skybackup file to move data to another PC. "
                "AES-encrypted — restore only in a licensed copy of SkyAdmin Pro."
            ),
        )
        backup.grid(row=row, column=0, sticky="ew")
        backup_body = backup.body
        backup_btns = ctk.CTkFrame(backup_body, fg_color="transparent")
        backup_btns.grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.backup_action_btn = ctk.CTkButton(
            backup_btns, text="Backup encrypted data…", width=200, command=self._backup_encrypted
        )
        self.backup_action_btn.pack(side="left", padx=(0, 8))
        self.restore_backup_btn = ctk.CTkButton(
            backup_btns,
            text="Restore encrypted backup…",
            width=200,
            fg_color="transparent",
            border_width=1,
            command=self._restore_encrypted,
        )
        self.restore_backup_btn.pack(side="left")
        self.backup_banner = ctk.CTkLabel(backup_body, text="", anchor="w", justify="left")
        self.backup_banner.grid(row=1, column=0, sticky="ew")
        bind_wrap_label(self.backup_banner, backup_body, pad=24)

        # Auto-backup toggle + retention / restore path
        auto_frame = ctk.CTkFrame(backup_body, fg_color="transparent")
        auto_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        from skyadmin_pro.services.auto_backup import (
            SETTING_AUTO_BACKUP_ENABLED,
            SETTING_AUTO_BACKUP_INTERVAL,
            retention_help_text,
        )

        self._auto_backup_enabled_var = ctk.StringVar(
            value="1" if self.app.db.get_setting(SETTING_AUTO_BACKUP_ENABLED) == "1" else "0"
        )
        self._auto_backup_interval_var = ctk.StringVar(
            value=self.app.db.get_setting(SETTING_AUTO_BACKUP_INTERVAL) or "daily"
        )
        ctk.CTkSwitch(
            auto_frame,
            text="Auto-backup",
            variable=self._auto_backup_enabled_var,
            onvalue="1",
            offvalue="0",
            command=self._toggle_auto_backup,
        ).pack(side="left", padx=(0, 12))
        return auto_frame, backup_body, retention_help_text

    def _SettingsView_build_data_tab_backup_p2(self, auto_frame, backup_body, retention_help_text):
        ctk.CTkOptionMenu(
            auto_frame,
            variable=self._auto_backup_interval_var,
            values=["daily", "weekly", "off"],
            width=100,
            command=lambda _: self._toggle_auto_backup(),
        ).pack(side="left", padx=(0, 12))
        ctk.CTkButton(
            auto_frame,
            text="Open AutoBackups folder",
            width=180,
            fg_color="transparent",
            border_width=1,
            command=self._open_auto_backups_folder,
        ).pack(side="left")
        self.auto_backup_retention_label = ctk.CTkLabel(
            backup_body,
            text=retention_help_text(),
            anchor="w",
            justify="left",
            text_color=TEXT_MUTED,
        )
        self.auto_backup_retention_label.grid(row=3, column=0, sticky="ew", pady=(6, 0))
        bind_wrap_label(self.auto_backup_retention_label, backup_body, pad=24)
