from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.widgets import SectionCard, bind_wrap_label, themed_entry


class SettingsViewMixin11:
    def _SettingsView_build_data_tab_backup_p1(self, scroll, row):
        backup = SectionCard(
            scroll,
            title="Encrypted data backup",
            subtitle=(
                "A full .skybackup is the entire database plus all workspace files "
                "(not a partial sync). AES-encrypted — restore only in a licensed copy. "
                "Tip: point the backup folder at a Google Drive Desktop path."
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
        self._SettingsView_build_backup_destination(backup_body)
        return self._SettingsView_build_data_tab_backup_auto(backup_body)

    def _SettingsView_build_data_tab_backup_auto(self, backup_body):
        auto_frame = ctk.CTkFrame(backup_body, fg_color="transparent")
        auto_frame.grid(row=4, column=0, sticky="ew", pady=(8, 0))
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

    def _SettingsView_build_backup_destination(self, backup_body) -> None:
        from skyadmin_pro.services.auto_backup import auto_backups_dir

        dest_frame = ctk.CTkFrame(backup_body, fg_color="transparent")
        dest_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        dest_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(dest_frame, text="Backup folder:").grid(row=0, column=0, sticky="w")
        self._backup_dest_var = ctk.StringVar(value=str(auto_backups_dir(self.app.paths.root, self.app.db)))
        themed_entry(dest_frame, textvariable=self._backup_dest_var).grid(row=0, column=1, sticky="ew", padx=(8, 8))
        ctk.CTkButton(dest_frame, text="Browse…", width=80, command=self._browse_backup_destination).grid(
            row=0, column=2, padx=(0, 4)
        )
        ctk.CTkButton(
            dest_frame,
            text="Save",
            width=64,
            fg_color="transparent",
            border_width=1,
            command=self._save_backup_destination,
        ).grid(row=0, column=3, padx=(0, 4))
        ctk.CTkButton(
            dest_frame,
            text="Open folder",
            width=100,
            fg_color="transparent",
            border_width=1,
            command=self._open_auto_backups_folder,
        ).grid(row=0, column=4)
        hint = ctk.CTkLabel(
            backup_body,
            text="Invalid/empty path uses {workspace}/AutoBackups. Use a Google Drive Desktop folder for cloud copies.",
            anchor="w",
            justify="left",
            text_color=TEXT_MUTED,
        )
        hint.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        bind_wrap_label(hint, backup_body, pad=24)
