"""Settings view — appearance, license, portal URL, and local paths."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from skyadmin_pro.config import (
    CHECKLIST_TEMPLATES,
    DEFAULT_COLOR_THEME,
    DEFAULT_PORTAL_URL,
    MOBILE_VIEWER_URL,
    OWNER_EMAIL,
    PRICING_DEFAULT_SERVICE,
    SERVICE_TYPES,
    SETTING_APPEARANCE_MODE,
    SETTING_COLOR_THEME,
    SETTING_PORTAL_URL,
    SETTING_WORKSPACE_CUSTOM,
    SETTING_WORKSPACE_ROOT,
    TRANSACTION_RANGES,
    pricing_uses_transaction_ranges,
)
from skyadmin_pro.paths import WorkspacePaths
from skyadmin_pro.services.data_hygiene import run_data_hygiene
from skyadmin_pro.services.file_ops import open_in_file_manager
from skyadmin_pro.services.workflow import normalize_portal_url, repair_client_workspaces
from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.widgets import FeedbackLabel, bind_wrap_label, labeled_entry, make_modal, option_menu_style_kwargs, themed_entry


from skyadmin_pro.ui.views.settings.backup_mixin import BackupMixin
from skyadmin_pro.ui.views.settings.checklist_mixin import ChecklistMixin
from skyadmin_pro.ui.views.settings.license_mixin import LicenseMixin
from skyadmin_pro.ui.views.settings.pricing_mixin import PricingMixin
from skyadmin_pro.ui.views.settings.workspace_mixin import WorkspaceMixin

class SettingsView(BackupMixin, ChecklistMixin, LicenseMixin, PricingMixin, WorkspaceMixin, BaseView):
    title = "Settings"
    subtitle = "Appearance, portal URL, workspace folders, and local database location."

    def build(self) -> None:
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)
        scroll = ctk.CTkScrollableFrame(self.body, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        self._checklist_rows: list[tuple[ctk.CTkFrame, ctk.StringVar, ctk.StringVar]] = []

        card = ctk.CTkFrame(scroll, corner_radius=12)
        card.grid(row=1, column=0, sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card,
            text="Appearance",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(18, 8))

        ctk.CTkLabel(card, text="Theme", anchor="w").grid(row=1, column=0, sticky="w", padx=20)
        self.appearance_menu = ctk.CTkOptionMenu(
            card,
            values=["Dark", "Light", "System"],
            command=self._on_appearance_change,
            width=160,
        )
        self.appearance_menu.grid(row=1, column=1, sticky="w", padx=20, pady=(8, 0))

        ctk.CTkLabel(card, text="Accent", anchor="w").grid(row=2, column=0, sticky="w", padx=20, pady=(12, 0))
        self.color_theme_menu = ctk.CTkOptionMenu(
            card,
            values=["blue", "green", "dark-blue"],
            command=self._on_color_theme_change,
            width=160,
        )
        self.color_theme_menu.grid(row=2, column=1, sticky="w", padx=20, pady=(12, 0))

        # Tagline (sidebar subtitle) — user-editable
        ctk.CTkLabel(card, text="Tagline", anchor="w").grid(row=3, column=0, sticky="w", padx=20, pady=(12, 0))
        tag_row = ctk.CTkFrame(card, fg_color="transparent")
        tag_row.grid(row=3, column=1, sticky="ew", padx=20, pady=(12, 0))
        tag_row.grid_columnconfigure(0, weight=1)
        self.tagline_var = ctk.StringVar()
        themed_entry(tag_row, textvariable=self.tagline_var).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(tag_row, text="Save", width=70, command=self._save_tagline).grid(row=0, column=1, padx=(8, 0))

        # Language
        ctk.CTkLabel(card, text="Language", anchor="w").grid(row=4, column=0, sticky="w", padx=20, pady=(12, 0))
        from skyadmin_pro.services.i18n import available_languages

        self.lang_menu = ctk.CTkOptionMenu(
            card,
            values=[lang.upper() for lang in available_languages()],
            command=self._on_language_change,
            width=120,
        )
        self.lang_menu.grid(row=4, column=1, sticky="w", padx=20, pady=(12, 0))

        # License — directly under Appearance
        ctk.CTkLabel(
            card,
            text="License",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).grid(row=5, column=0, columnspan=2, sticky="w", padx=20, pady=(16, 4))
        self.license_label = ctk.CTkLabel(
            card,
            text="License: checking…",
            anchor="w",
            text_color=TEXT_MUTED,
        )
        self.license_label.grid(row=6, column=0, columnspan=2, sticky="ew", padx=20)
        bind_wrap_label(self.license_label, card, pad=44)

        sync_row = ctk.CTkFrame(card, fg_color="transparent")
        sync_row.grid(row=7, column=0, columnspan=2, sticky="ew", padx=20, pady=(6, 0))
        sync_row.grid_columnconfigure(0, weight=1)
        self.daily_sync_label = ctk.CTkLabel(
            sync_row,
            text="",
            anchor="w",
            text_color=TEXT_MUTED,
            justify="left",
        )
        self.daily_sync_label.grid(row=0, column=0, sticky="ew")
        bind_wrap_label(self.daily_sync_label, sync_row, pad=110)
        self.data_sync_label = ctk.CTkLabel(
            sync_row,
            text="",
            anchor="w",
            text_color=TEXT_MUTED,
            justify="left",
        )
        self.data_sync_label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        bind_wrap_label(self.data_sync_label, sync_row, pad=16)
        sync_btns = ctk.CTkFrame(sync_row, fg_color="transparent")
        sync_btns.grid(row=0, column=1, sticky="e", padx=(12, 0))
        self.sync_now_btn = ctk.CTkButton(sync_btns, text="Sync Now", width=90, command=self._sync_now)
        self.sync_now_btn.pack(side="top", pady=(0, 4))
        self.conflicts_btn = ctk.CTkButton(
            sync_btns,
            text="Conflicts",
            width=90,
            fg_color="transparent",
            border_width=1,
            state="disabled",
            command=self._open_sync_conflicts,
        )
        self.conflicts_btn.pack(side="top")
        self.check_updates_btn = ctk.CTkButton(
            sync_btns,
            text="Check updates",
            width=90,
            fg_color="transparent",
            border_width=1,
            command=self._check_for_updates,
        )
        self.check_updates_btn.pack(side="top", pady=(4, 0))
        if (MOBILE_VIEWER_URL or "").strip():
            ctk.CTkButton(
                sync_btns,
                text="Mobile viewer",
                width=90,
                fg_color="transparent",
                border_width=1,
                command=self._open_mobile_viewer,
            ).pack(side="top", pady=(4, 0))

        lic_buttons = ctk.CTkFrame(card, fg_color="transparent")
        lic_buttons.grid(row=8, column=0, columnspan=2, sticky="ew", padx=20, pady=(10, 0))
        lic_buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            lic_buttons,
            text="Activate / Manage License…",
            command=self._open_activation,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=3)
        ctk.CTkButton(
            lic_buttons,
            text="License Agreement",
            fg_color="transparent",
            border_width=1,
            command=self._show_license,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=3)
        ctk.CTkButton(
            lic_buttons,
            text="Disclaimer",
            fg_color="transparent",
            border_width=1,
            command=self._show_disclaimer,
        ).grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=3)
        if MOBILE_VIEWER_URL:
            ctk.CTkButton(
                lic_buttons,
                text="Mobile Viewer",
                fg_color="transparent",
                border_width=1,
                command=self._open_mobile_viewer,
            ).grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=3)

        key_row = ctk.CTkFrame(card, fg_color="transparent")
        key_row.grid(row=9, column=0, columnspan=2, sticky="ew", padx=20, pady=(14, 0))
        key_row.grid_columnconfigure(0, weight=1)
        self.key_paste_var = ctk.StringVar()
        self.key_field = labeled_entry(
            key_row,
            "Paste License Key",
            textvariable=self.key_paste_var,
            placeholder_text="Paste the full License Key here…",
        )
        self.key_field.grid(row=0, column=0, sticky="ew")
        self.key_field.bind("<Return>", lambda _e: self._activate_with_key())
        ctk.CTkButton(key_row, text="Activate", width=110, command=self._activate_with_key).grid(
            row=0, column=1, sticky="e", padx=(10, 0)
        )

        pass_row = ctk.CTkFrame(card, fg_color="transparent")
        pass_row.grid(row=10, column=0, columnspan=2, sticky="ew", padx=20, pady=(12, 18))
        pass_row.grid_columnconfigure(0, weight=1)
        self.passcode_var = ctk.StringVar()
        self.passcode_field = labeled_entry(
            pass_row,
            "Or paste Passcode (SKYPASS1)",
            textvariable=self.passcode_var,
            placeholder_text="SKYPASS1:…",
        )
        self.passcode_field.grid(row=0, column=0, sticky="ew")
        self.passcode_field.bind("<Return>", lambda _e: self._activate_with_passcode())
        ctk.CTkButton(pass_row, text="Activate", width=110, command=self._activate_with_passcode).grid(
            row=0, column=1, sticky="e", padx=(10, 0)
        )

        portal = ctk.CTkFrame(scroll, corner_radius=12)
        portal.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        portal.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            portal,
            text="Semi-auto portal uploader",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(18, 6))
        ctk.CTkLabel(
            portal,
            text="Opened in the browser when you click Open Portal. The file path is copied for Ctrl+V.",
            wraplength=720,
            justify="left",
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, columnspan=2, sticky="ew", padx=20)
        ctk.CTkLabel(portal, text="Portal URL", anchor="w").grid(row=2, column=0, sticky="w", padx=20, pady=(12, 16))
        self.portal_var = ctk.StringVar()
        themed_entry(portal, textvariable=self.portal_var).grid(row=2, column=1, sticky="ew", padx=20, pady=(12, 8))
        ctk.CTkButton(portal, text="Save portal URL", width=140, command=self._save_portal).grid(
            row=3, column=1, sticky="w", padx=20, pady=(0, 16)
        )

        pricing = ctk.CTkFrame(scroll, corner_radius=12)
        pricing.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        pricing.grid_columnconfigure(0, weight=1)
        self._pricing_rows: dict[str, dict] = {}
        self._selected_pricing_id: int | None = None

        ctk.CTkLabel(
            pricing,
            text="Service pricing matrix",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            pricing,
            text=(
                "Fee, SLA, headcount, and required documents per service. "
                "Accounting services use transaction-volume tiers; other services "
                "use named charge lines (e.g. DBD fee, registration fee, package base). "
                "Company Details → Tax IDs auto-fills accounting tiers when you change Transaction Volume."
            ),
            wraplength=720,
            justify="left",
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=20)

        pricing_toolbar = ctk.CTkFrame(pricing, fg_color="transparent")
        pricing_toolbar.grid(row=2, column=0, sticky="ew", padx=20, pady=(12, 8))
        pricing_toolbar.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(pricing_toolbar, text="Service", anchor="w").grid(row=0, column=0, padx=(0, 8))
        self.pricing_service_menu = ctk.CTkOptionMenu(
            pricing_toolbar,
            values=[PRICING_DEFAULT_SERVICE],
            command=self._on_pricing_service_change,
            width=320,
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
            pricing,
            columns=(
                ("range", "Transaction range", 220),
                ("monthly", "Monthly THB", 100),
                ("annual", "Annual THB", 100),
                ("sla", "SLA hrs", 70),
                ("hc", "HC", 40),
                ("docs", "Required docs", 260),
            ),
            on_select=self._on_pricing_row_select,
            showheight=6,
        )
        self.pricing_tree.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 8))

        pricing_form = ctk.CTkFrame(pricing, fg_color="transparent")
        pricing_form.grid(row=4, column=0, sticky="ew", padx=20)
        pricing_form.grid_columnconfigure((1, 3), weight=1)
        self.pricing_range_var = ctk.StringVar()
        self.pricing_monthly_var = ctk.StringVar()
        self.pricing_annual_var = ctk.StringVar()
        self.pricing_sla_var = ctk.StringVar()
        self.pricing_headcount_var = ctk.StringVar()
        self.pricing_docs_var = ctk.StringVar()

        self.pricing_range_heading = ctk.CTkLabel(pricing_form, text="Transaction range", anchor="w")
        self.pricing_range_heading.grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.pricing_charge_entry = themed_entry(
            pricing_form,
            textvariable=self.pricing_range_var,
        )
        self.pricing_range_menu = ctk.CTkOptionMenu(
            pricing_form,
            variable=self.pricing_range_var,
            values=list(TRANSACTION_RANGES),
            width=280,
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
        pricing_buttons = ctk.CTkFrame(pricing, fg_color="transparent")
        pricing_buttons.grid(row=5, column=0, sticky="w", padx=20, pady=(8, 16))
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

        services = ctk.CTkFrame(scroll, corner_radius=12)
        services.grid(row=4, column=0, sticky="ew", pady=(16, 0))
        services.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            services,
            text="Services list",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            services,
            text=(
                "One service per line. These appear in the Service dropdowns "
                "(Service Pipeline, Company Details, expiry alerts)."
            ),
            wraplength=720,
            justify="left",
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=20)
        self.services_text = ctk.CTkTextbox(services, height=170)
        self.services_text.grid(row=2, column=0, sticky="ew", padx=20, pady=(12, 8))
        services_buttons = ctk.CTkFrame(services, fg_color="transparent")
        services_buttons.grid(row=3, column=0, sticky="w", padx=20, pady=(0, 16))
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

        directory = ctk.CTkFrame(scroll, corner_radius=12)
        directory.grid(row=5, column=0, sticky="ew", pady=(16, 0))
        directory.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            directory,
            text="Department list (Office Hub)",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            directory,
            text=(
                "Master list for Department in Office Hub → Contacts. "
                "Company names come from your Clients list (Database & Tasks) — "
                "the Organization field is a client company picker, not a separate list. "
                "Type a new department in a contact form to add it automatically, or import "
                "from existing contacts below."
            ),
            wraplength=720,
            justify="left",
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=20)

        self.departments_text = ctk.CTkTextbox(directory, height=140)
        self.departments_text.grid(row=2, column=0, sticky="ew", padx=20, pady=(12, 4))

        dir_buttons = ctk.CTkFrame(directory, fg_color="transparent")
        dir_buttons.grid(row=3, column=0, sticky="w", padx=20, pady=(8, 16))
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

        checklists = ctk.CTkFrame(scroll, corner_radius=12)
        checklists.grid(row=6, column=0, sticky="ew", pady=(16, 0))
        checklists.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            checklists,
            text="Renewal checklists",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))
        checklist_desc = ctk.CTkLabel(
            checklists,
            text=(
                "The Renewals tab (Database & Tasks) seeds each company's checklist "
                "from one of these lists, picked by the service you select "
                "(e.g. Passport → Passport Renewal, Visa/Work Permit → Visa Renewal, "
                "other services → General Renewal). Items companies already have are "
                "kept, so edit freely. "
                "Days = how many days before expiry the item should be done (0 = after renewal)."
            ),
            justify="left",
            text_color=TEXT_MUTED,
            anchor="w",
        )
        checklist_desc.grid(row=1, column=0, sticky="ew", padx=20)
        bind_wrap_label(checklist_desc, checklists, pad=44)

        picker = ctk.CTkFrame(checklists, fg_color="transparent")
        picker.grid(row=2, column=0, sticky="ew", padx=20, pady=(12, 4))
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
        themed_entry(picker, textvariable=self._new_list_var, width=170).grid(
            row=0, column=3, sticky="ew", padx=(8, 8)
        )
        ctk.CTkButton(picker, text="Add", width=56, command=self._add_checklist_list).grid(row=0, column=4, padx=(0, 8))
        ctk.CTkButton(
            picker,
            text="Delete list",
            width=96,
            fg_color="transparent",
            border_width=1,
            command=self._delete_checklist_list,
        ).grid(row=0, column=5)

        self.checklist_scroll = ctk.CTkScrollableFrame(checklists, height=170)
        self.checklist_scroll.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 4))
        self.checklist_scroll.grid_columnconfigure(0, weight=1)

        add_row = ctk.CTkFrame(checklists, fg_color="transparent")
        add_row.grid(row=4, column=0, sticky="ew", padx=20, pady=(4, 4))
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

        checklist_buttons = ctk.CTkFrame(checklists, fg_color="transparent")
        checklist_buttons.grid(row=5, column=0, sticky="w", padx=20, pady=(4, 16))
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

        info = ctk.CTkFrame(scroll, corner_radius=12)
        info.grid(row=7, column=0, sticky="ew", pady=(16, 0))
        info.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            info,
            text="Local paths",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(18, 8))

        ctk.CTkLabel(info, text="Workspace root", anchor="w", text_color=TEXT_MUTED).grid(
            row=1, column=0, sticky="nw", padx=20, pady=(0, 6)
        )
        workspace_row = ctk.CTkFrame(info, fg_color="transparent")
        workspace_row.grid(row=1, column=1, sticky="ew", padx=20, pady=(0, 6))
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
            row=2, column=0, sticky="nw", padx=20, pady=(0, 6)
        )
        self.path_labels["Clients"] = self._path_row(info, row=2, on_open=self._open_clients)

        ctk.CTkLabel(info, text="Suppliers", anchor="w", text_color=TEXT_MUTED).grid(
            row=3, column=0, sticky="nw", padx=20, pady=(0, 6)
        )
        self.path_labels["Suppliers"] = self._path_row(info, row=3, on_open=self._open_suppliers)

        ctk.CTkLabel(info, text="Database", anchor="w", text_color=TEXT_MUTED).grid(
            row=4, column=0, sticky="nw", padx=20, pady=(0, 18)
        )
        self.db_value = ctk.CTkLabel(info, text="", anchor="w", wraplength=720)
        self.db_value.grid(row=4, column=1, sticky="w", padx=20, pady=(0, 18))

        self.integrity_banner = ctk.CTkLabel(
            info,
            text="",
            anchor="w",
            justify="left",
            wraplength=720,
            text_color=("#b45309", "#fbbf24"),
        )
        self.integrity_banner.grid(row=5, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 8))

        # Diagnostics — email the log tail to the owner for remote support
        diag_row = ctk.CTkFrame(info, fg_color="transparent")
        diag_row.grid(row=6, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 16))
        ctk.CTkButton(
            diag_row,
            text="✉ Email diagnostics to support",
            width=230,
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

        # Encrypted backup — the ONLY supported way to copy data between PCs now
        backup = ctk.CTkFrame(scroll, corner_radius=12, border_color=("#bfdbfe", "#1e3a5f"), border_width=1)
        backup.grid(row=8, column=0, sticky="ew", pady=(16, 0))
        backup.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            backup,
            text="🔒 Encrypted Data Backup — for copying data to another PC",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(16, 4))
        ctk.CTkLabel(
            backup,
            text=(
                "To move your data to another PC, create an encrypted backup "
                "(.skybackup) and copy that single file over — then Restore it there. "
                "The backup is AES-encrypted and can only be restored by a licensed "
                "copy of SkyAdmin Pro. Do NOT copy the raw folders — they are not protected."
            ),
            wraplength=720,
            justify="left",
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 8))
        ctk.CTkButton(backup, text="Backup Encrypted Data…", width=200, command=self._backup_encrypted).grid(
            row=2, column=0, sticky="w", padx=20, pady=(0, 12)
        )
        ctk.CTkButton(
            backup,
            text="Restore Encrypted Backup…",
            width=200,
            fg_color="transparent",
            border_width=1,
            command=self._restore_encrypted,
        ).grid(row=2, column=1, sticky="w", padx=(8, 20), pady=(0, 12))
        self.backup_banner = ctk.CTkLabel(backup, text="", anchor="w", justify="left", wraplength=720)
        self.backup_banner.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 14))

        # Disclaimer — top of Settings
        disclaimer = ctk.CTkFrame(scroll, corner_radius=12, border_color=("#e5e7eb", "#374151"), border_width=1)
        disclaimer.grid(row=0, column=0, sticky="ew")
        disclaimer.grid_columnconfigure(0, weight=1)

        # Update banner (hidden unless an update is advertised via control list)
        self.update_frame = ctk.CTkFrame(scroll, corner_radius=12, fg_color=("#dbeafe", "#1e3a5f"))
        self.update_frame.grid_columnconfigure(0, weight=1)
        self.update_label = ctk.CTkLabel(self.update_frame, text="", anchor="w", justify="left", wraplength=680)
        self.update_label.grid(row=0, column=0, sticky="ew", padx=20, pady=(12, 4))
        self._update_download_btn = ctk.CTkButton(
            self.update_frame,
            text="Download",
            width=120,
            command=self._open_update_url,
        )
        self._update_download_btn.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 12))
        ctk.CTkLabel(
            disclaimer,
            text="© 2026 Sky Creation Innovations — Proprietary Software. All Rights Reserved.",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(16, 4))
        ctk.CTkLabel(
            disclaimer,
            text=(
                "SkyAdmin Pro — including its source code, design, UI/UX, database "
                "schema, icons, and all assets — is the exclusive intellectual property "
                "of Sky Creation Innovations. No person or organization may copy, "
                "reproduce, redistribute, reverse-engineer, claim credit for, or create "
                "derivative works from any part of this software without prior written "
                "permission.\n\n"
                "This software is protected under the Copyright Act B.E. 2537 (1994) of "
                "Thailand (as amended B.E. 2558), the Computer Crimes Act B.E. 2550 "
                "(2007) of Thailand, and the Copyright Law of the Republic of the Union "
                "of Myanmar (2019), together with all applicable international "
                "treaties. Unauthorized copying, distribution, or use may result in "
                "civil liability and criminal prosecution in Thailand and/or Myanmar.\n\n"
                "Licensed use only: this copy is hardware-locked and will not run "
                "without a valid activation code issued by Sky Creation Innovations. "
                "Governing law: Kingdom of Thailand and Republic of the Union of Myanmar."
            ),
            wraplength=720,
            justify="left",
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 16))

        self.feedback = FeedbackLabel(scroll)
        self.feedback.grid(row=7, column=0, sticky="ew", pady=(12, 0))

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
            or __import__("skyadmin_pro.config", fromlist=["APP_TAGLINE"]).APP_TAGLINE
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
        # Disclaimer license status
        self._refresh_license_label()
        self._refresh_backup_banner()
        self._refresh_integrity_banner()
        self._refresh_update_banner()

    def _path_row(self, info, *, row: int, on_open) -> ctk.CTkLabel:
        frame = ctk.CTkFrame(info, fg_color="transparent")
        frame.grid(row=row, column=1, sticky="ew", padx=20, pady=(0, 6))
        frame.grid_columnconfigure(0, weight=1)
        value = ctk.CTkLabel(frame, text="", anchor="w")
        value.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(frame, text="Open", width=70, fg_color="transparent", border_width=1, command=on_open).grid(
            row=0, column=1, padx=(8, 0)
        )
        return value

