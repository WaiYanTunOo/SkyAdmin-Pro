from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.widgets import SectionCard, themed_textbox


class SettingsViewMixin5:
    def _build_business_tab_directory(self, scroll, row: int) -> int:
        directory = SectionCard(
            scroll,
            title="Department list (Office Hub)",
            subtitle=(
                "Master list for Department in Office Hub → Contacts. "
                "Company names come from Clients — type a new department in a contact form to add it."
            ),
        )
        directory.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        dir_body = directory.body
        dir_body.grid_columnconfigure(0, weight=1)
        self.departments_text = themed_textbox(dir_body, height=120)
        self.departments_text.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        dir_buttons = ctk.CTkFrame(dir_body, fg_color="transparent")
        dir_buttons.grid(row=1, column=0, sticky="w")
        ctk.CTkButton(dir_buttons, text="Save departments", width=140, command=self._save_directory_lists).grid(
            row=0, column=0
        )
        ctk.CTkButton(
            dir_buttons,
            text="Import from data",
            width=140,
            fg_color="transparent",
            border_width=1,
            command=self._import_directory_lists,
        ).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(
            dir_buttons,
            text="Import clients CSV",
            width=140,
            fg_color="transparent",
            border_width=1,
            command=self._import_clients_csv,
        ).grid(row=0, column=2, padx=(8, 0))
        return row + 1

    def _build_business_tab_checklists(self, scroll, row: int) -> int:
        add_row, cl_body = self._SettingsView_build_business_tab_checkli_p1(scroll, row)
        self._SettingsView_build_business_tab_checkli_p2(add_row, cl_body)
        return row + 1

    def _build_data_tab(self, tab) -> None:
        scroll = self._scroll_tab(tab)
        row = 0
        row = self._build_data_tab_backup(scroll, row)
        row = self._SettingsView_build_drive_card(scroll, row)
        row = self._build_data_tab_advanced(scroll, row)

    def _build_data_tab_backup(self, scroll, row: int) -> int:
        auto_frame, backup_body, retention_help_text = self._SettingsView_build_data_tab_backup_p1(scroll, row)
        self._SettingsView_build_data_tab_backup_p2(auto_frame, backup_body, retention_help_text)
        return row + 1

    def _build_data_tab_advanced(self, scroll, row: int) -> int:
        advanced = SectionCard(
            scroll,
            title="Advanced Database Settings",
            subtitle="Low-level options for performance tuning. Requires app restart.",
        )
        advanced.grid(row=row, column=0, sticky="ew", pady=(8, 0))
        adv_body = advanced.body
        self._wal_mode_var = ctk.StringVar(value=self.app.db.get_setting("db_wal_mode", "1"))
        ctk.CTkSwitch(
            adv_body,
            text="Enable WAL (Write-Ahead Logging) mode for concurrent reads",
            variable=self._wal_mode_var,
            onvalue="1",
            offvalue="0",
            command=self._toggle_wal_mode,
        ).pack(anchor="w", pady=(4, 0))
        return row + 1

    def _toggle_wal_mode(self) -> None:
        self.app.db.set_setting("db_wal_mode", self._wal_mode_var.get())
        from tkinter import messagebox

        messagebox.showinfo(
            "Restart Required", "Database mode changed. Please restart SkyAdmin Pro for changes to take effect."
        )
