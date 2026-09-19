from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import MOBILE_VIEWER_URL, SETTING_SYNC_AUTO_INTERVAL
from skyadmin_pro.services.data_sync import normalize_sync_auto_interval


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
        self._data_sync_cb = ctk.CTkCheckBox(
            sync_opts,
            text="Enable optional cloud data sync (this licensed PC only)",
            variable=self.data_sync_var,
            command=self._on_data_sync_toggle,
        )
        self._data_sync_cb.pack(anchor="w")
        auto_row = ctk.CTkFrame(sync_opts, fg_color="transparent")
        auto_row.pack(anchor="w", pady=(8, 0))
        ctk.CTkLabel(auto_row, text="Auto sync every:").pack(side="left", padx=(0, 8))
        self._sync_auto_interval_var = ctk.StringVar(
            value=normalize_sync_auto_interval(self.app.db.get_setting(SETTING_SYNC_AUTO_INTERVAL))
        )
        self._sync_auto_menu = ctk.CTkOptionMenu(
            auto_row,
            variable=self._sync_auto_interval_var,
            values=["off", "15", "30", "60"],
            width=90,
            command=lambda _: self._on_sync_auto_interval(),
        )
        self._sync_auto_menu.pack(side="left")
        ctk.CTkLabel(auto_row, text="seconds (off = manual / dirty push only)").pack(side="left", padx=(8, 0))

        self._SettingsView_build_mobile_vault(body)

        ctk.CTkButton(body, text="Activate / Manage License…", command=self._open_activation).grid(
            row=6, column=0, sticky="ew", pady=(12, 0)
        )
