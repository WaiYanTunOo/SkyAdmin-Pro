from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED


class SettingsViewMixin12:
    def _SettingsView_build_mobile_vault(self, body) -> None:
        frame = ctk.CTkFrame(body, fg_color="transparent")
        frame.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text="Mobile Vault Passphrase", anchor="w").grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            frame,
            text="Unlocks portal passwords on the phone viewer. Stored as verifier only — never synced.",
            text_color=TEXT_MUTED,
            wraplength=520,
            justify="left",
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(2, 6))
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew")
        self.mobile_vault_entry = ctk.CTkEntry(row, placeholder_text="Min 8 characters", show="•", width=240)
        self.mobile_vault_entry.pack(side="left", padx=(0, 8))
        ctk.CTkButton(row, text="Save", width=70, command=self._save_mobile_vault).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            row, text="Clear", width=70, fg_color="transparent", border_width=1, command=self._clear_mobile_vault
        ).pack(side="left")
        self.mobile_vault_status = ctk.CTkLabel(frame, text="", text_color=TEXT_MUTED, anchor="w")
        self.mobile_vault_status.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        self._refresh_mobile_vault_status()
