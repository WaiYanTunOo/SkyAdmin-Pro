from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.widgets import SectionCard, bind_wrap_label, themed_entry


class SettingsViewMixin7:
    def _SettingsView_build_general_tab_paths_p1(self, scroll, row):
        paths = SectionCard(
            scroll,
            title="Local paths",
            subtitle="Workspace root, client/supplier folders, and SQLite database location.",
        )
        paths.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        info = paths.body
        info.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(info, text="Workspace root", anchor="w", text_color=TEXT_MUTED).grid(
            row=0, column=0, sticky="nw", pady=(0, 6)
        )
        workspace_row = ctk.CTkFrame(info, fg_color="transparent")
        workspace_row.grid(row=0, column=1, sticky="ew", pady=(0, 6))
        workspace_row.grid_columnconfigure(0, weight=1)
        self.workspace_var = ctk.StringVar()
        themed_entry(workspace_row, textvariable=self.workspace_var).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(workspace_row, text="Browse…", width=80, command=self._browse_workspace).grid(
            row=0, column=1, padx=(8, 0)
        )
        ctk.CTkButton(workspace_row, text="Save", width=70, command=self._save_workspace).grid(
            row=0, column=2, padx=(8, 0)
        )
        ctk.CTkButton(
            workspace_row,
            text="Repair client folders",
            width=150,
            fg_color="transparent",
            border_width=1,
            command=self._repair_client_folders,
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))
        ctk.CTkButton(
            workspace_row,
            text="Run data hygiene",
            width=140,
            command=self._run_data_hygiene,
        ).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

        self.path_labels: dict[str, ctk.CTkLabel] = {}
        ctk.CTkLabel(info, text="Clients", anchor="w", text_color=TEXT_MUTED).grid(
            row=1, column=0, sticky="nw", pady=(0, 6)
        )
        self.path_labels["Clients"] = self._path_row(info, row=1, on_open=self._open_clients)

        ctk.CTkLabel(info, text="Suppliers", anchor="w", text_color=TEXT_MUTED).grid(
            row=2, column=0, sticky="nw", pady=(0, 6)
        )
        self.path_labels["Suppliers"] = self._path_row(info, row=2, on_open=self._open_suppliers)

        ctk.CTkLabel(info, text="Database", anchor="w", text_color=TEXT_MUTED).grid(
            row=3, column=0, sticky="nw", pady=(0, 6)
        )
        return info

    def _SettingsView_build_general_tab_paths_p2(self, info):
        self.db_value = ctk.CTkLabel(info, text="", anchor="w")
        self.db_value.grid(row=3, column=1, sticky="w", pady=(0, 6))
        bind_wrap_label(self.db_value, info, pad=120)

        self.integrity_banner = ctk.CTkLabel(
            info,
            text="",
            anchor="w",
            justify="left",
            text_color=("#b45309", "#fbbf24"),
        )
        self.integrity_banner.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        bind_wrap_label(self.integrity_banner, info, pad=24)

        diag_row = ctk.CTkFrame(info, fg_color="transparent")
        diag_row.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ctk.CTkButton(
            diag_row,
            text="Email diagnostics to support",
            width=220,
            fg_color="transparent",
            border_width=1,
            command=self._email_diagnostics,
        ).pack(side="left")
        ctk.CTkButton(
            diag_row,
            text="Check database integrity",
            width=180,
            fg_color="transparent",
            border_width=1,
            command=self._run_integrity_check,
        ).pack(side="left", padx=(8, 0))
