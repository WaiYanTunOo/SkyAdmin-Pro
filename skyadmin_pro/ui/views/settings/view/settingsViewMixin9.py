from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import MOBILE_VIEWER_URL


class SettingsViewMixin9:
    def _SettingsView_build_license_tab_status_p2(self, sync_btns, body):
        self.audit_log_btn = ctk.CTkButton(
            sync_btns,
            text="Audit log",
            width=90,
            fg_color="transparent",
            border_width=1,
            command=self._open_audit_log,
        )
        self.audit_log_btn.pack(side="left", padx=(0, 8))
        self.check_updates_btn = ctk.CTkButton(
            sync_btns,
            text="Check updates",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=self._check_for_updates,
        )
        self.check_updates_btn.pack(side="left", padx=(0, 8))
        if (MOBILE_VIEWER_URL or "").strip():
            ctk.CTkButton(
                sync_btns,
                text="Mobile viewer",
                width=110,
                fg_color="transparent",
                border_width=1,
                command=self._open_mobile_viewer,
            ).pack(side="left")

        self.data_sync_var = ctk.BooleanVar(value=False)
        sync_opts = ctk.CTkFrame(body, fg_color="transparent")
        sync_opts.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        ctk.CTkCheckBox(
            sync_opts,
            text="Enable optional cloud data sync (this licensed PC only)",
            variable=self.data_sync_var,
            command=self._on_data_sync_toggle,
        ).pack(anchor="w")

        self._SettingsView_build_mobile_vault(body)

        ctk.CTkButton(body, text="Activate / Manage License…", command=self._open_activation).grid(
            row=6, column=0, sticky="ew", pady=(12, 0)
        )
