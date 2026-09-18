from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import LEGAL_DISCLAIMER_SHORT
from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.widgets import SectionCard, bind_wrap_label, card_style_kwargs, labeled_entry, themed_entry


class SettingsViewMixin2:
    def _build_general_tab_portal(self, scroll, row: int) -> int:
        portal = SectionCard(
            scroll,
            title="Semi-auto portal uploader",
            subtitle="Opened in the browser when you click Open Portal. The file path is copied for Ctrl+V.",
        )
        portal.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        portal_body = portal.body
        portal_body.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(portal_body, text="Portal URL", anchor="w").grid(row=0, column=0, sticky="w", pady=4)
        self.portal_var = ctk.StringVar()
        themed_entry(portal_body, textvariable=self.portal_var).grid(row=0, column=1, sticky="ew", pady=4)
        ctk.CTkButton(portal_body, text="Save portal URL", width=140, command=self._save_portal).grid(
            row=1, column=1, sticky="w", pady=(4, 0)
        )
        return row + 1

    def _build_general_tab_disclaimer(self, scroll, row: int) -> int:
        disclaimer = ctk.CTkFrame(scroll, corner_radius=12, **card_style_kwargs())
        disclaimer.grid(row=row, column=0, sticky="ew")
        disclaimer.grid_columnconfigure(0, weight=1)
        self.disclaimer_label = ctk.CTkLabel(
            disclaimer,
            text=LEGAL_DISCLAIMER_SHORT,
            anchor="w",
            justify="left",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=11),
        )
        self.disclaimer_label.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 8))
        bind_wrap_label(self.disclaimer_label, disclaimer, pad=32)
        legal_btns = ctk.CTkFrame(disclaimer, fg_color="transparent")
        legal_btns.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))
        ctk.CTkButton(
            legal_btns,
            text="License Agreement",
            fg_color="transparent",
            border_width=1,
            command=self._show_license,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            legal_btns,
            text="Disclaimer",
            fg_color="transparent",
            border_width=1,
            command=self._show_disclaimer,
        ).pack(side="left")
        return row + 1

    def _build_license_tab(self, tab) -> None:
        scroll = self._scroll_tab(tab)
        row = 0
        row = self._build_license_tab_status(scroll, row)
        row = self._build_license_tab_activate(scroll, row)

    def _build_license_tab_status(self, scroll, row: int) -> int:
        body, sync_btns = self._SettingsView_build_license_tab_status_p1(scroll, row)
        self._SettingsView_build_license_tab_status_p2(sync_btns, body)
        return row + 1

    def _build_license_tab_activate(self, scroll, row: int) -> int:
        activate = SectionCard(
            scroll,
            title="Activate with key or passcode",
            subtitle="Paste a full license key, or a SKYPASS1 passcode from your administrator.",
        )
        activate.grid(row=row, column=0, sticky="ew")
        act_body = activate.body
        act_body.grid_columnconfigure(0, weight=1)

        self.key_paste_var = ctk.StringVar()
        self.passcode_var = ctk.StringVar()
        act_row = ctk.CTkFrame(act_body, fg_color="transparent")
        act_row.grid(row=0, column=0, sticky="ew")
        act_row.grid_columnconfigure(0, weight=1)
        self.key_field = labeled_entry(
            act_row,
            "License key or passcode",
            textvariable=self.key_paste_var,
            placeholder_text="Paste license key or SKYPASS1:…",
        )
        self.key_field.grid(row=0, column=0, sticky="ew")
        self.passcode_field = self.key_field
        self.key_field.bind("<Return>", lambda _e: self._activate_pasted())
        ctk.CTkButton(act_row, text="Activate", width=110, command=self._activate_pasted).grid(
            row=0, column=1, sticky="e", padx=(10, 0)
        )
        return row + 1

    def _build_business_tab(self, tab) -> None:
        scroll = self._scroll_tab(tab)
        row = 0
        row = self._build_business_tab_pricing(scroll, row)
        row = self._build_business_tab_services(scroll, row)
        row = self._build_business_tab_directory(scroll, row)
        row = self._build_business_tab_checklists(scroll, row)
