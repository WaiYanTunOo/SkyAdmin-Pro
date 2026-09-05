"""Settings view — appearance, license, portal URL, and local paths."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import (
    APP_TAGLINE,
    DEFAULT_COLOR_THEME,
    DEFAULT_PORTAL_URL,
    LEGAL_DISCLAIMER_SHORT,
    MOBILE_VIEWER_URL,
    PRICING_DEFAULT_SERVICE,
    SETTING_COLOR_THEME,
    SETTING_PORTAL_URL,
    TRANSACTION_RANGES,
)
from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.views.settings.backup_mixin import BackupMixin
from skyadmin_pro.ui.views.settings.checklist_mixin import ChecklistMixin
from skyadmin_pro.ui.views.settings.license_mixin import LicenseMixin
from skyadmin_pro.ui.views.settings.pricing_mixin import PricingMixin
from skyadmin_pro.ui.views.settings.workspace_mixin import WorkspaceMixin
from skyadmin_pro.ui.widgets import (
    FeedbackLabel,
    SectionCard,
    bind_wrap_label,
    card_style_kwargs,
    labeled_entry,
    option_menu_style_kwargs,
    themed_entry,
    themed_scrollable_frame,
    themed_tabview,
    themed_textbox,
)


class SettingsView(BackupMixin, ChecklistMixin, LicenseMixin, PricingMixin, WorkspaceMixin, BaseView):
    title = "Settings"
    subtitle = "Appearance, license, business defaults, and local data."

    def build(self) -> None:
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=0)
        self.body.grid_rowconfigure(1, weight=1)

        self.feedback = FeedbackLabel(self.body)
        self.feedback.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self.tabs = themed_tabview(self.body)
        self.tabs.grid(row=1, column=0, sticky="nsew", pady=(0, 0))

        self._checklist_rows: list[tuple[ctk.CTkFrame, ctk.StringVar, ctk.StringVar]] = []
        self._pricing_rows: dict[str, dict] = {}
        self._selected_pricing_id: int | None = None

        for name in ("General", "License", "Business", "Data & backup"):
            self.tabs.add(name)
            tab = self.tabs.tab(name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_propagate(True)

        self._build_general_tab(self.tabs.tab("General"))
        self._build_license_tab(self.tabs.tab("License"))
        self._build_business_tab(self.tabs.tab("Business"))
        self._build_data_tab(self.tabs.tab("Data & backup"))

    def _scroll_tab(self, tab) -> ctk.CTkScrollableFrame:
        scroll = themed_scrollable_frame(tab)
        scroll.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        scroll.grid_columnconfigure(0, weight=1)
        return scroll

    def _build_general_tab(self, tab) -> None:
        scroll = self._scroll_tab(tab)
        row = 0

        self.update_frame = ctk.CTkFrame(scroll, corner_radius=12, fg_color=("#dbeafe", "#1e3a5f"))
        self.update_frame.grid_columnconfigure(0, weight=1)
        self.update_label = ctk.CTkLabel(self.update_frame, text="", anchor="w", justify="left")
        self.update_label.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        bind_wrap_label(self.update_label, self.update_frame, pad=32)
        self._update_download_btn = ctk.CTkButton(
            self.update_frame,
            text="Download",
            width=120,
            command=self._open_update_url,
        )
        self._update_download_btn.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))
        self.update_frame.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        self.update_frame.grid_remove()
        row += 1

        appearance = SectionCard(
            scroll,
            title="Appearance",
            subtitle="Theme, accent color, sidebar tagline, and UI language.",
        )
        appearance.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        body = appearance.body
        body.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(body, text="Theme", anchor="w").grid(row=0, column=0, sticky="w", pady=4)
        self.appearance_menu = ctk.CTkOptionMenu(
            body,
            values=["Dark", "Light", "System"],
            command=self._on_appearance_change,
            width=160,
        )
        self.appearance_menu.grid(row=0, column=1, sticky="w", pady=4)

        ctk.CTkLabel(body, text="Accent", anchor="w").grid(row=1, column=0, sticky="w", pady=4)
        self.color_theme_menu = ctk.CTkOptionMenu(
            body,
            values=["blue", "green", "dark-blue"],
            command=self._on_color_theme_change,
            width=160,
        )
        self.color_theme_menu.grid(row=1, column=1, sticky="w", pady=4)

        ctk.CTkLabel(body, text="Tagline", anchor="w").grid(row=2, column=0, sticky="nw", pady=4)
        tag_row = ctk.CTkFrame(body, fg_color="transparent")
        tag_row.grid(row=2, column=1, sticky="ew", pady=4)
        tag_row.grid_columnconfigure(0, weight=1)
        self.tagline_var = ctk.StringVar()
        themed_entry(tag_row, textvariable=self.tagline_var).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(tag_row, text="Save", width=70, command=self._save_tagline).grid(row=0, column=1, padx=(8, 0))

        ctk.CTkLabel(body, text="Language", anchor="w").grid(row=3, column=0, sticky="w", pady=4)
        from skyadmin_pro.services.i18n import available_languages

        self.lang_menu = ctk.CTkOptionMenu(
            body,
            values=[lang.upper() for lang in available_languages()],
            command=self._on_language_change,
            width=120,
        )
        self.lang_menu.grid(row=3, column=1, sticky="w", pady=4)

        from skyadmin_pro.ui.theme import TEXT_MUTED

        ctk.CTkLabel(
            body,
            text="Shortcuts (outside text fields):  Ctrl+F search   ·   Ctrl+E export   ·   "
            "Ctrl+N new client   ·   Ctrl+Z undo   ·   Ctrl+D theme",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="w",
            justify="left",
        ).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        row += 1

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
        row += 1

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

    def _build_license_tab(self, tab) -> None:
        scroll = self._scroll_tab(tab)
        row = 0

        status = SectionCard(
            scroll,
            title="License & sync",
            subtitle=(
                "License check and optional cloud backup for this PC only. "
                "Each buyer's data is separate on the server. "
                "For a second PC, use Data & backup → encrypted backup (.skybackup)."
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
        self.sync_now_btn = ctk.CTkButton(sync_btns, text="Sync now", width=100, command=self._sync_now)
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

        ctk.CTkButton(body, text="Activate / Manage License…", command=self._open_activation).grid(
            row=5, column=0, sticky="ew", pady=(12, 0)
        )
        row += 1

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

    def _build_business_tab(self, tab) -> None:
        scroll = self._scroll_tab(tab)
        row = 0

        pricing = SectionCard(
            scroll,
            title="Service pricing matrix",
            subtitle=(
                "Fee, SLA, headcount, and required documents per service. "
                "Accounting uses transaction-volume tiers; other services use named charge lines."
            ),
        )
        pricing.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        pricing_body = pricing.body
        pricing_body.grid_columnconfigure(0, weight=1)

        pricing_toolbar = ctk.CTkFrame(pricing_body, fg_color="transparent")
        pricing_toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        pricing_toolbar.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(pricing_toolbar, text="Service", anchor="w").grid(row=0, column=0, padx=(0, 8))
        self.pricing_service_menu = ctk.CTkOptionMenu(
            pricing_toolbar,
            values=[PRICING_DEFAULT_SERVICE],
            command=self._on_pricing_service_change,
            width=280,
        )
        self.pricing_service_menu.grid(row=0, column=1, sticky="w")
        ctk.CTkButton(
            pricing_toolbar,
            text="Reset service",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=self._reset_service_pricing,
        ).grid(row=0, column=2, padx=(8, 0))
        ctk.CTkButton(
            pricing_toolbar,
            text="Seed all services",
            width=130,
            fg_color="transparent",
            border_width=1,
            command=self._seed_all_service_pricing,
        ).grid(row=0, column=3, padx=(8, 0))

        self.pricing_tree = ThemedTreeview(
            pricing_body,
            columns=(
                ("range", "Transaction range", 200),
                ("monthly", "Monthly THB", 100),
                ("annual", "Annual THB", 100),
                ("sla", "SLA hrs", 70),
                ("hc", "HC", 40),
                ("docs", "Required docs", 240),
            ),
            on_select=self._on_pricing_row_select,
            showheight=6,
        )
        self.pricing_tree.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        pricing_form = ctk.CTkFrame(pricing_body, fg_color="transparent")
        pricing_form.grid(row=2, column=0, sticky="ew")
        pricing_form.grid_columnconfigure((1, 3), weight=1)
        self.pricing_range_var = ctk.StringVar()
        self.pricing_monthly_var = ctk.StringVar()
        self.pricing_annual_var = ctk.StringVar()
        self.pricing_sla_var = ctk.StringVar()
        self.pricing_headcount_var = ctk.StringVar()
        self.pricing_docs_var = ctk.StringVar()

        self.pricing_range_heading = ctk.CTkLabel(pricing_form, text="Transaction range", anchor="w")
        self.pricing_range_heading.grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.pricing_charge_entry = themed_entry(pricing_form, textvariable=self.pricing_range_var)
        self.pricing_range_menu = ctk.CTkOptionMenu(
            pricing_form,
            variable=self.pricing_range_var,
            values=list(TRANSACTION_RANGES),
            width=260,
        )
        self.pricing_range_menu.grid(row=0, column=1, sticky="ew", pady=4)
        self.pricing_monthly_label = ctk.CTkLabel(pricing_form, text="Monthly fee (THB)", anchor="w")
        self.pricing_monthly_label.grid(row=0, column=2, sticky="w", padx=(16, 8), pady=4)
        self.pricing_monthly_entry = themed_entry(pricing_form, textvariable=self.pricing_monthly_var, width=120)
        self.pricing_monthly_entry.grid(row=0, column=3, sticky="ew", pady=4)
        ctk.CTkLabel(pricing_form, text="Annual fee (THB)", anchor="w").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self.pricing_annual_entry = themed_entry(pricing_form, textvariable=self.pricing_annual_var, width=120)
        self.pricing_annual_entry.grid(row=1, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(pricing_form, text="SLA hours", anchor="w").grid(row=1, column=2, sticky="w", padx=(16, 8), pady=4)
        self.pricing_sla_entry = themed_entry(pricing_form, textvariable=self.pricing_sla_var, width=120)
        self.pricing_sla_entry.grid(row=1, column=3, sticky="ew", pady=4)
        ctk.CTkLabel(pricing_form, text="Headcount", anchor="w").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        self.pricing_headcount_entry = themed_entry(pricing_form, textvariable=self.pricing_headcount_var, width=120)
        self.pricing_headcount_entry.grid(row=2, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(pricing_form, text="Required documents", anchor="w").grid(
            row=2, column=2, sticky="nw", padx=(16, 8), pady=4
        )
        self.pricing_docs_entry = themed_entry(pricing_form, textvariable=self.pricing_docs_var)
        self.pricing_docs_entry.grid(row=2, column=3, sticky="ew", pady=4)

        pricing_buttons = ctk.CTkFrame(pricing_body, fg_color="transparent")
        pricing_buttons.grid(row=3, column=0, sticky="w", pady=(8, 0))
        ctk.CTkButton(pricing_buttons, text="Save pricing row", width=140, command=self._save_pricing_tier).grid(
            row=0, column=0, padx=(0, 8)
        )
        self.pricing_add_charge_btn = ctk.CTkButton(
            pricing_buttons,
            text="Add charge line",
            width=130,
            fg_color="transparent",
            border_width=1,
            command=self._add_pricing_charge_line,
        )
        self.pricing_add_charge_btn.grid(row=0, column=1, padx=(0, 8))
        self.pricing_delete_charge_btn = ctk.CTkButton(
            pricing_buttons,
            text="Delete charge line",
            width=140,
            fg_color="transparent",
            border_width=1,
            command=self._delete_pricing_charge_line,
        )
        self.pricing_delete_charge_btn.grid(row=0, column=2)
        row += 1

        services = SectionCard(
            scroll,
            title="Services list",
            subtitle="One service per line — used in Service Pipeline, Company Details, and expiry alerts.",
        )
        services.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        services_body = services.body
        services_body.grid_columnconfigure(0, weight=1)
        self.services_text = themed_textbox(services_body, height=150)
        self.services_text.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        services_buttons = ctk.CTkFrame(services_body, fg_color="transparent")
        services_buttons.grid(row=1, column=0, sticky="w")
        ctk.CTkButton(services_buttons, text="Save services", width=140, command=self._save_services).grid(
            row=0, column=0
        )
        ctk.CTkButton(
            services_buttons,
            text="Reset to defaults",
            width=140,
            fg_color="transparent",
            border_width=1,
            command=self._reset_services,
        ).grid(row=0, column=1, padx=(8, 0))
        row += 1

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
        row += 1

        checklists = SectionCard(
            scroll,
            title="Renewal checklists",
            subtitle=(
                "Renewals tab seeds each company's checklist from these lists by service type. "
                "Days = how many days before expiry the item should be done (0 = after renewal)."
            ),
        )
        checklists.grid(row=row, column=0, sticky="ew")
        cl_body = checklists.body
        cl_body.grid_columnconfigure(0, weight=1)

        picker = ctk.CTkFrame(cl_body, fg_color="transparent")
        picker.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        picker.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(picker, text="List:").grid(row=0, column=0, sticky="w")
        self.checklist_menu = ctk.CTkOptionMenu(
            picker,
            values=[""],
            command=lambda _name: self._load_checklist_items(self.checklist_menu.get()),
            width=190,
            **option_menu_style_kwargs(),
        )
        self.checklist_menu.grid(row=0, column=1, sticky="w", padx=(8, 16))
        ctk.CTkLabel(picker, text="Add list:").grid(row=0, column=2, sticky="w")
        self._new_list_var = ctk.StringVar()
        themed_entry(picker, textvariable=self._new_list_var, width=170).grid(row=0, column=3, sticky="ew", padx=(8, 8))
        ctk.CTkButton(picker, text="Add", width=56, command=self._add_checklist_list).grid(row=0, column=4, padx=(0, 8))
        ctk.CTkButton(
            picker,
            text="Delete list",
            width=96,
            fg_color="transparent",
            border_width=1,
            command=self._delete_checklist_list,
        ).grid(row=0, column=5)

        self.checklist_scroll = ctk.CTkFrame(cl_body, fg_color="transparent")
        self.checklist_scroll.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        self.checklist_scroll.grid_columnconfigure(0, weight=1)

        add_row = ctk.CTkFrame(cl_body, fg_color="transparent")
        add_row.grid(row=2, column=0, sticky="ew", pady=(4, 4))
        add_row.grid_columnconfigure(0, weight=1)
        self._new_item_var = ctk.StringVar()
        themed_entry(add_row, textvariable=self._new_item_var, placeholder_text="New checklist task").grid(
            row=0, column=0, sticky="ew"
        )
        self._new_days_var = ctk.StringVar()
        themed_entry(add_row, textvariable=self._new_days_var, width=90, placeholder_text="days").grid(
            row=0, column=1, padx=(8, 0)
        )
        ctk.CTkButton(add_row, text="Add item", width=96, command=self._add_checklist_item).grid(
            row=0, column=2, padx=(8, 0)
        )

        checklist_buttons = ctk.CTkFrame(cl_body, fg_color="transparent")
        checklist_buttons.grid(row=3, column=0, sticky="w", pady=(4, 0))
        ctk.CTkButton(checklist_buttons, text="Save list", width=140, command=self._save_checklist).grid(
            row=0, column=0
        )
        ctk.CTkButton(
            checklist_buttons,
            text="Reset to defaults",
            width=150,
            fg_color="transparent",
            border_width=1,
            command=self._reset_checklist,
        ).grid(row=0, column=1, padx=(8, 0))

    def _build_data_tab(self, tab) -> None:
        scroll = self._scroll_tab(tab)
        row = 0

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
        row += 1

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

        # Auto-backup toggle
        auto_frame = ctk.CTkFrame(backup_body, fg_color="transparent")
        auto_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        from skyadmin_pro.services.auto_backup import (
            SETTING_AUTO_BACKUP_ENABLED,
            SETTING_AUTO_BACKUP_INTERVAL,
        )
        self._auto_backup_enabled_var = ctk.StringVar(
            value="1" if self.app.db.get_setting(SETTING_AUTO_BACKUP_ENABLED) == "1" else "0"
        )
        self._auto_backup_interval_var = ctk.StringVar(
            value=self.app.db.get_setting(SETTING_AUTO_BACKUP_INTERVAL) or "daily"
        )
        ctk.CTkSwitch(
            auto_frame, text="Auto-backup", variable=self._auto_backup_enabled_var,
            onvalue="1", offvalue="0", command=self._toggle_auto_backup,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkOptionMenu(
            auto_frame, variable=self._auto_backup_interval_var,
            values=["daily", "weekly", "off"], width=100,
            command=lambda _: self._toggle_auto_backup(),
        ).pack(side="left")

    def on_show(self) -> None:
        current = ctk.get_appearance_mode()
        self.appearance_menu.set(current)
        theme = self.app.db.get_setting(SETTING_COLOR_THEME, DEFAULT_COLOR_THEME) or DEFAULT_COLOR_THEME
        try:
            self.color_theme_menu.set(theme)
        except Exception:
            pass
        self.workspace_var.set(str(self.app.paths.root))
        self.tagline_var.set(
            self.app.db.get_setting("app_tagline")
            or APP_TAGLINE
        )
        saved_lang = (self.app.db.get_setting("ui_language") or "en").upper()
        try:
            self.lang_menu.set(saved_lang)
        except Exception:
            pass
        self.path_labels["Clients"].configure(text=str(self.app.paths.clients))
        self.path_labels["Suppliers"].configure(text=str(self.app.paths.suppliers))
        self.db_value.configure(text=str(self.app.db.db_file))
        self.portal_var.set(self.app.db.get_setting(SETTING_PORTAL_URL, DEFAULT_PORTAL_URL) or DEFAULT_PORTAL_URL)
        self.services_text.delete("1.0", "end")
        self.services_text.insert("1.0", "\n".join(self.app.db.list_service_types()))
        self._reload_checklists()
        self._load_directory_lists()
        self._refresh_pricing_services()
        self._refresh_pricing_matrix()
        self._refresh_license_label()
        self._refresh_backup_banner()
        self._refresh_integrity_banner()
        self._refresh_update_banner()
        from skyadmin_pro.config import SETTING_DATA_SYNC_ENABLED

        self.data_sync_var.set((self.app.db.get_setting(SETTING_DATA_SYNC_ENABLED) or "0").strip() == "1")

    def _path_row(self, info, *, row: int, on_open) -> ctk.CTkLabel:
        frame = ctk.CTkFrame(info, fg_color="transparent")
        frame.grid(row=row, column=1, sticky="ew", pady=(0, 6))
        frame.grid_columnconfigure(0, weight=1)
        value = ctk.CTkLabel(frame, text="", anchor="w")
        value.grid(row=0, column=0, sticky="ew")
        bind_wrap_label(value, frame, pad=90)
        ctk.CTkButton(frame, text="Open", width=70, fg_color="transparent", border_width=1, command=on_open).grid(
            row=0, column=1, padx=(8, 0)
        )
        return value

    def _open_audit_log(self) -> None:
        from skyadmin_pro.ui.views.audit_log import AuditLogDialog
        AuditLogDialog(self.app)
