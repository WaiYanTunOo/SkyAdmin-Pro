"""Settings view — appearance, license, portal URL, and local paths."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk

from skyadmin_pro.config import (
    CHECKLIST_TEMPLATES,
    DEFAULT_COLOR_THEME,
    DEFAULT_PORTAL_URL,
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
from skyadmin_pro.ui.widgets import FeedbackLabel


class SettingsView(BaseView):
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
        ctk.CTkEntry(tag_row, textvariable=self.tagline_var).grid(row=0, column=0, sticky="ew")
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
        self.daily_sync_label = ctk.CTkLabel(
            card,
            text="",
            anchor="w",
            text_color=TEXT_MUTED,
            wraplength=500,
            justify="left",
        )
        self.daily_sync_label.grid(row=7, column=0, sticky="w", padx=20, pady=(2, 0))
        ctk.CTkButton(card, text="Sync Now", width=90, command=self._sync_now).grid(
            row=7, column=1, sticky="e", padx=20, pady=(2, 0)
        )
        lic_buttons = ctk.CTkFrame(card, fg_color="transparent")
        lic_buttons.grid(row=8, column=0, columnspan=2, sticky="w", padx=20, pady=(6, 0))
        ctk.CTkButton(
            lic_buttons,
            text="Activate / Manage License…",
            width=200,
            command=self._open_activation,
        ).pack(side="left")
        ctk.CTkButton(
            lic_buttons,
            text="License Agreement",
            width=150,
            fg_color="transparent",
            border_width=1,
            command=self._show_license,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            lic_buttons,
            text="Disclaimer",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=self._show_disclaimer,
        ).pack(side="left", padx=(8, 0))

        # Full license key paste box
        ctk.CTkLabel(
            card,
            text="Paste License Key:",
            anchor="w",
        ).grid(row=9, column=0, columnspan=2, sticky="w", padx=20, pady=(12, 2))
        key_row = ctk.CTkFrame(card, fg_color="transparent")
        key_row.grid(row=10, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 4))
        key_row.grid_columnconfigure(0, weight=1)
        self.key_paste_var = ctk.StringVar()
        key_entry = ctk.CTkEntry(
            key_row,
            textvariable=self.key_paste_var,
            placeholder_text="Paste the full License Key here…",
        )
        key_entry.grid(row=0, column=0, sticky="ew")
        key_entry.bind("<Return>", lambda _e: self._activate_with_key())
        ctk.CTkButton(key_row, text="Activate", width=110, command=self._activate_with_key).grid(
            row=0, column=1, padx=(8, 0)
        )

        # Quick passcode activation (8-digit code from the owner)
        ctk.CTkLabel(
            card,
            text="Or enter 8-digit Passcode:",
            anchor="w",
        ).grid(row=11, column=0, columnspan=2, sticky="w", padx=20, pady=(8, 2))
        pass_row = ctk.CTkFrame(card, fg_color="transparent")
        pass_row.grid(row=12, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 18))
        self.passcode_var = ctk.StringVar()
        pc_entry = ctk.CTkEntry(
            pass_row,
            textvariable=self.passcode_var,
            placeholder_text="8-digit passcode…",
            width=210,
        )
        pc_entry.grid(row=0, column=0, sticky="w")
        pc_entry.bind("<Return>", lambda _e: self._activate_with_passcode())
        ctk.CTkButton(pass_row, text="Activate", width=110, command=self._activate_with_passcode).grid(
            row=0, column=1, padx=(8, 0)
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
        ctk.CTkEntry(portal, textvariable=self.portal_var).grid(row=2, column=1, sticky="ew", padx=20, pady=(12, 8))
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
        self.pricing_charge_entry = ctk.CTkEntry(
            pricing_form,
            textvariable=self.pricing_range_var,
            width=280,
        )
        self.pricing_range_menu = ctk.CTkOptionMenu(
            pricing_form,
            variable=self.pricing_range_var,
            values=list(TRANSACTION_RANGES),
            width=280,
        )
        self.pricing_range_menu.grid(row=0, column=1, sticky="w", pady=4)
        self.pricing_monthly_label = ctk.CTkLabel(pricing_form, text="Monthly fee (THB)", anchor="w")
        self.pricing_monthly_label.grid(row=0, column=2, sticky="w", padx=(16, 8), pady=4)
        ctk.CTkEntry(pricing_form, textvariable=self.pricing_monthly_var, width=120).grid(
            row=0, column=3, sticky="w", pady=4
        )
        ctk.CTkLabel(pricing_form, text="Annual fee (THB)", anchor="w").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self.pricing_annual_entry = ctk.CTkEntry(pricing_form, textvariable=self.pricing_annual_var, width=120)
        self.pricing_annual_entry.grid(row=1, column=1, sticky="w", pady=4)
        ctk.CTkLabel(pricing_form, text="SLA hours", anchor="w").grid(row=1, column=2, sticky="w", padx=(16, 8), pady=4)
        ctk.CTkEntry(pricing_form, textvariable=self.pricing_sla_var, width=120).grid(
            row=1, column=3, sticky="w", pady=4
        )
        ctk.CTkLabel(pricing_form, text="Headcount", anchor="w").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        self.pricing_headcount_entry = ctk.CTkEntry(pricing_form, textvariable=self.pricing_headcount_var, width=120)
        self.pricing_headcount_entry.grid(row=2, column=1, sticky="w", pady=4)
        ctk.CTkLabel(pricing_form, text="Required documents", anchor="w").grid(
            row=2, column=2, sticky="nw", padx=(16, 8), pady=4
        )
        ctk.CTkEntry(pricing_form, textvariable=self.pricing_docs_var).grid(row=2, column=3, sticky="ew", pady=4)
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
        ctk.CTkLabel(
            checklists,
            text=(
                "The Renewals tab (Database & Tasks) seeds each company's checklist "
                "from one of these lists, picked by the service you select "
                "(e.g. Passport → Passport Renewal, Visa/Work Permit → Visa Renewal, "
                "other services → General Renewal). Items companies already have are "
                "kept, so edit freely. "
                "Days = how many days before expiry the item should be done (0 = after renewal)."
            ),
            wraplength=720,
            justify="left",
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=20)

        picker = ctk.CTkFrame(checklists, fg_color="transparent")
        picker.grid(row=2, column=0, sticky="ew", padx=20, pady=(12, 4))
        picker.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(picker, text="List:").grid(row=0, column=0, sticky="w")
        self.checklist_menu = ctk.CTkOptionMenu(
            picker, values=[""], command=lambda _name: self._load_checklist_items(self.checklist_menu.get()), width=190
        )
        self.checklist_menu.grid(row=0, column=1, sticky="w", padx=(8, 16))
        ctk.CTkLabel(picker, text="Add list:").grid(row=0, column=2, sticky="w")
        self._new_list_var = ctk.StringVar()
        new_list_entry = ctk.CTkEntry(picker, textvariable=self._new_list_var, width=170)
        new_list_entry.grid(row=0, column=3, sticky="ew", padx=(8, 8))
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
        ctk.CTkEntry(add_row, textvariable=self._new_item_var, placeholder_text="New checklist task").grid(
            row=0, column=0, sticky="ew"
        )
        self._new_days_var = ctk.StringVar()
        ctk.CTkEntry(add_row, textvariable=self._new_days_var, width=90, placeholder_text="days").grid(
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
        ctk.CTkEntry(workspace_row, textvariable=self.workspace_var).grid(row=0, column=0, sticky="ew")
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

        # Diagnostics — email the log tail to the owner for remote support
        diag_row = ctk.CTkFrame(info, fg_color="transparent")
        diag_row.grid(row=5, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 16))
        ctk.CTkButton(
            diag_row,
            text="✉ Email diagnostics to support",
            width=230,
            fg_color="transparent",
            border_width=1,
            command=self._email_diagnostics,
        ).pack(side="left")

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
        self._refresh_update_banner()

    def _refresh_update_banner(self) -> None:
        from skyadmin_pro.config import APP_VERSION
        from skyadmin_pro.services.license import (
            is_newer_version,
            read_update_info,
        )

        info = read_update_info()
        if info and is_newer_version(info["version"], APP_VERSION):
            self.update_label.configure(text=(f"⬆ Update available: v{info['version']} (you have v{APP_VERSION})."))
            self._update_url = info.get("url") or ""
            self.update_frame.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        else:
            self.update_frame.grid_forget()

    def _open_update_url(self) -> None:
        import webbrowser

        url = getattr(self, "_update_url", "")
        if url:
            webbrowser.open(url)

    def _email_diagnostics(self) -> None:
        import webbrowser
        from urllib.parse import quote

        from skyadmin_pro.services.license import get_machine_id

        log_tail = ""
        try:
            log_path = Path.home() / ".skyadmin_pro" / "app.log"
            if log_path.exists():
                lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
                log_tail = "\n".join(lines[-40:])
        except Exception:
            pass
        body = (
            f"Machine ID: {get_machine_id()}\n"
            f"Workspace: {self.app.paths.root}\n\n"
            "--- app.log (last 40 lines) ---\n"
            f"{log_tail}\n"
        )
        subject = "SkyAdmin Pro — Diagnostics"
        webbrowser.open(f"mailto:{OWNER_EMAIL}?subject={quote(subject)}&body={quote(body)}")

    def _refresh_backup_banner(self) -> None:
        from datetime import date as _date

        from skyadmin_pro.config import SETTING_LAST_ENCRYPTED_BACKUP

        raw = self.app.db.get_setting(SETTING_LAST_ENCRYPTED_BACKUP)
        if not raw:
            self.backup_banner.configure(
                text="⚠ You have NEVER created an encrypted backup — your data "
                "has no off-machine copy. Create one now (2 minutes).",
                text_color=("#b45309", "#fbbf24"),
            )
            return
        try:
            last = _date.fromisoformat(str(raw)[:10])
            days = (_date.today() - last).days
        except ValueError:
            days = 999
        if days >= 7:
            self.backup_banner.configure(
                text=f"⚠ Last encrypted backup was {days} day(s) ago — create a fresh one.",
                text_color=("#b45309", "#fbbf24"),
            )
        else:
            self.backup_banner.configure(
                text=f"✓ Last encrypted backup: {last.isoformat()} ({days} day(s) ago).",
                text_color=("#15803d", "#4ade80"),
            )

    def _reload_checklists(self, keep: str | None = None) -> None:
        names = self.app.db.list_checklist_template_names()
        current = keep or self.checklist_menu.get()
        self.checklist_menu.configure(values=names)
        if current in names:
            self.checklist_menu.set(current)
        elif names:
            self.checklist_menu.set(names[0])
        self._load_checklist_items(self.checklist_menu.get())

    def _load_checklist_items(self, name: str) -> None:
        for frame, *_ in self._checklist_rows:
            frame.destroy()
        self._checklist_rows.clear()
        for entry in self.app.db.get_checklist_template_items(name):
            self._add_checklist_row(str(entry.get("item") or ""), str(entry.get("due_days") or 0))

    def _add_checklist_row(self, item: str, days: str) -> None:
        row = ctk.CTkFrame(self.checklist_scroll, fg_color="transparent")
        row.grid_columnconfigure(0, weight=1)
        item_var = ctk.StringVar(value=item)
        days_var = ctk.StringVar(value=days)
        ctk.CTkEntry(row, textvariable=item_var).grid(row=0, column=0, sticky="ew")
        days_entry = ctk.CTkEntry(row, textvariable=days_var, width=90)
        days_entry.grid(row=0, column=1, padx=(6, 0))
        ctk.CTkButton(
            row,
            text="✕",
            width=36,
            fg_color="transparent",
            border_width=1,
            command=lambda f=row: self._remove_checklist_row(f),
        ).grid(row=0, column=2, padx=(6, 0))
        row.pack(fill="x", padx=6, pady=3)
        self._checklist_rows.append((row, item_var, days_var))

    def _remove_checklist_row(self, frame: ctk.CTkFrame) -> None:
        for index, (current, *_) in enumerate(self._checklist_rows):
            if current is frame:
                self._checklist_rows.pop(index)
                frame.destroy()
                return

    def _add_checklist_item(self) -> None:
        item = self._new_item_var.get().strip()
        days_raw = self._new_days_var.get().strip() or "0"
        if not item:
            self.feedback.error("Enter the checklist task text.")
            return
        try:
            days = int(days_raw)
        except ValueError:
            self.feedback.error("Days before expiry must be a number.")
            return
        self._add_checklist_row(item, str(days))
        self._new_item_var.set("")
        self._new_days_var.set("")

    def _save_checklist(self) -> None:
        name = self.checklist_menu.get().strip()
        rows: list[tuple[str, int]] = []
        for _, item_var, days_var in self._checklist_rows:
            item = item_var.get().strip()
            if not item:
                continue
            try:
                days = int(days_var.get().strip() or "0")
            except ValueError:
                self.feedback.error(f"Days for “{item[:30]}…” must be a number.")
                return
            rows.append((item, days))
        if not rows:
            self.feedback.error("Add at least one checklist item.")
            return
        try:
            self.app.db.set_checklist_template_items(name, rows)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self._reload_checklists(keep=name)
        self.feedback.success(f"Checklist “{name}” saved.")
        self.app.set_status(f"Renewal checklist “{name}” updated.")

    def _add_checklist_list(self) -> None:
        name = self._new_list_var.get().strip()
        if not name:
            self.feedback.error("Enter a name for the new checklist.")
            return
        try:
            self.app.db.add_checklist_template(name)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self._new_list_var.set("")
        self._reload_checklists(keep=name)
        self.feedback.success(f"Checklist “{name}” added — add items, then Save.")

    def _delete_checklist_list(self) -> None:
        name = self.checklist_menu.get().strip()
        if not name:
            self.feedback.error("Select a checklist first.")
            return
        builtin = {template_name for template_name, _ in CHECKLIST_TEMPLATES}
        if name in builtin:
            self.feedback.error(f"“{name}” is a built-in list — edit it instead.")
            return
        if not messagebox.askyesno(
            "Delete checklist",
            f"Delete the checklist “{name}”?\n\nCompanies already seeded keep their items.",
            parent=self.winfo_toplevel(),
        ):
            return
        self.app.db.delete_checklist_template(name)
        self._reload_checklists()
        self.feedback.success(f"Checklist “{name}” deleted.")

    def _reset_checklist(self) -> None:
        name = self.checklist_menu.get().strip()
        if not name:
            self.feedback.error("Select a checklist first.")
            return
        self.app.db.reset_checklist_template(name)
        self._reload_checklists(keep=name)
        self.feedback.success(f"Checklist “{name}” reset to the default items.")

    def _save_services(self) -> None:
        lines = self.services_text.get("1.0", "end").splitlines()
        names = [ln.strip() for ln in lines if ln.strip()]
        try:
            self.app.db.set_service_types(names)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.on_show()
        self._refresh_service_menus()
        self.feedback.success("Services list saved.")
        self.app.set_status("Services list updated.")

    def _reset_services(self) -> None:
        self.app.db.set_service_types(list(SERVICE_TYPES))
        self.on_show()
        self._refresh_service_menus()
        self.feedback.success("Services reset to the default list.")
        self.app.set_status("Services list reset to defaults.")

    def _refresh_service_menus(self) -> None:
        view = self.app._views.get("database_tasks")
        if view is None:
            return
        view.refresh_all()

    def _backup_encrypted(self) -> None:
        dest = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Save Encrypted Backup",
            defaultextension=".skybackup",
            initialfile=f"SkyAdminPro_Backup_{__import__('datetime').date.today().isoformat()}.skybackup",
            filetypes=[("SkyAdmin Backup", "*.skybackup"), ("All files", "*.*")],
        )
        if not dest:
            return
        self.feedback.info("Creating encrypted backup… please wait.")
        self.configure(cursor="watch")
        self.update_idletasks()
        import threading

        def _worker():
            err = None
            try:
                from skyadmin_pro.services.crypto import create_encrypted_backup

                create_encrypted_backup(self.app.paths.root, self.app.db.db_file, Path(dest))
            except Exception as exc:
                err = str(exc)

            def _done():
                if not self.winfo_exists():
                    return
                self.configure(cursor="")
                if err:
                    self.feedback.error(f"Backup failed: {err}")
                else:
                    self.feedback.success(f"Encrypted backup saved: {Path(dest).name}")
                    from datetime import date as _d

                    from skyadmin_pro.config import SETTING_LAST_ENCRYPTED_BACKUP

                    self.app.db.set_setting(SETTING_LAST_ENCRYPTED_BACKUP, _d.today().isoformat())
                    self._refresh_backup_banner()
                    self.app.set_status(f"Backup saved to {dest}")

            try:
                self.after(0, _done)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _restore_encrypted(self) -> None:
        src = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Restore Encrypted Backup",
            filetypes=[("SkyAdmin Backup", "*.skybackup"), ("All files", "*.*")],
        )
        if not src:
            return
        if not messagebox.askyesno(
            "Restore backup",
            "This will overwrite your current database and workspace files with the backup contents.\n\nContinue?",
            parent=self.winfo_toplevel(),
        ):
            return
        self.feedback.info("Restoring encrypted backup… please wait.")
        self.configure(cursor="watch")
        self.update_idletasks()
        import threading

        def _worker():
            err = None
            safety_path = None
            try:
                from datetime import datetime as _dt

                from skyadmin_pro.services.crypto import (
                    create_encrypted_backup,
                    restore_encrypted_backup,
                )

                backup_dir = self.app.db.db_file.parent / "backups"
                backup_dir.mkdir(parents=True, exist_ok=True)
                stamp = _dt.now().strftime("%Y%m%d_%H%M%S")
                safety_path = backup_dir / f"pre_restore_{stamp}.skybackup"
                create_encrypted_backup(self.app.paths.root, self.app.db.db_file, safety_path)
                # Note: shutdown() is NOT called here - it's unsafe from a worker thread.
                # The restore operation will handle the DB file directly.
                restore_encrypted_backup(Path(src), self.app.paths.root, self.app.db.db_file)
            except Exception as exc:
                err = str(exc)

            def _done():
                if not self.winfo_exists():
                    return
                self.configure(cursor="")
                if err:
                    self.feedback.error(f"Restore failed: {err}")
                else:
                    extra = ""
                    if safety_path is not None:
                        extra = f"\n\nSafety backup saved:\n{safety_path}"
                    self.feedback.success("Restore complete — please restart the app.")
                    self.app.set_status("Restore complete — restart required")
                    messagebox.showinfo(
                        "Restore complete",
                        f"Backup restored successfully.{extra}\n\nPlease close and reopen SkyAdmin Pro.",
                        parent=self.winfo_toplevel(),
                    )

            try:
                self.after(0, _done)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _browse_workspace(self) -> None:
        initial = self.workspace_var.get().strip() or str(Path.home())
        folder = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            title="Choose workspace folder",
            initialdir=initial if Path(initial).is_dir() else str(Path.home()),
        )
        if folder:
            self.workspace_var.set(str(Path(folder).resolve()))

    def _save_workspace(self) -> None:
        raw = self.workspace_var.get().strip()
        if not raw:
            self.feedback.error("Enter a workspace path.")
            return
        root = Path(raw).expanduser().resolve()
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.feedback.error(f"Cannot create the workspace folder: {exc}")
            return
        self.app.db.set_setting(SETTING_WORKSPACE_ROOT, str(root))
        # Explicit user choice — stop auto-normalizing to the exe folder.
        self.app.db.set_setting(SETTING_WORKSPACE_CUSTOM, "1")
        self.app.paths = WorkspacePaths(root)
        self.app.paths.ensure()
        self.on_show()
        self.feedback.success(f"Workspace changed to {root}")
        self.app.set_status(f"Workspace: {root}")

    def _repair_client_folders(self) -> None:
        names = self.app.db.list_client_names()
        if not names:
            self.feedback.error("No clients in the database.")
            return
        result = repair_client_workspaces(self.app.paths.clients, names)
        linked = int(result["linked"])
        created = int(result["created"])
        failed = int(result["failed"])
        if failed:
            self.feedback.error(
                f"Repaired {linked} linked, {created} created, {failed} failed. "
                f"Check: {', '.join(result['failed_names'][:3])}"
            )
            return
        self.feedback.success(f"Client folders OK — {linked} linked to existing folders, {created} newly created.")
        self.app.set_status(f"Client folders: {linked} linked, {created} created, {result['total']} total")

    def _run_data_hygiene(self) -> None:
        if not messagebox.askyesno(
            "Run data hygiene",
            "This will:\n"
            "• Refresh service pricing (flat-fee vs transaction tiers)\n"
            "• Import departments from contacts\n"
            "• Link/create client workspace folders\n"
            "• Roll forward stale annual expiry dates (31 Dec services)\n"
            "• Migrate any legacy IRD passwords to Office Hub\n"
            "• Infer accounting service types from documents (Tax IDs rollout)\n"
            "• Import client liaison contacts into Office Hub\n"
            "• Infer VO/CSH renewal dates from document expiry\n\n"
            "Continue?",
            parent=self.winfo_toplevel(),
        ):
            return
        try:
            result = run_data_hygiene(self.app.db, self.app.paths.clients)
        except Exception as exc:
            self.feedback.error(str(exc))
            return
        self._load_directory_lists()
        self._refresh_pricing_services()
        self._refresh_pricing_matrix()
        failed = int(result["folders_failed"])
        msg = (
            f"Pricing refreshed · {result['departments_imported']} dept(s) imported · "
            f"{result['expiry_dates_rolled']} expiry date(s) rolled forward · "
            f"{result.get('service_types_inferred', 0)} service type(s) inferred · "
            f"{result.get('liaison_contacts_created', 0)} liaison contact(s) imported · "
            f"{result.get('vo_renewals_inferred', 0)} VO + "
            f"{result.get('csh_renewals_inferred', 0)} CSH renewal(s) inferred · "
            f"{result.get('ird_passwords_migrated', 0)} IRD password(s) migrated · "
            f"{result['folders_linked']} folder(s) linked · "
            f"{result['folders_created']} folder(s) created"
        )
        if failed:
            self.feedback.error(f"{msg} · {failed} folder(s) failed")
        else:
            self.feedback.success(msg)
        self.app.set_status("Data hygiene complete")

    def _open_clients(self) -> None:
        self._open_path(self.app.paths.clients)

    def _open_suppliers(self) -> None:
        self._open_path(self.app.paths.suppliers)

    def _open_path(self, path: Path) -> None:
        try:
            open_in_file_manager(path)
        except Exception as exc:
            self.feedback.error(str(exc))

    def _on_appearance_change(self, choice: str) -> None:
        mode = choice.lower()
        ctk.set_appearance_mode(mode)
        self.app.db.set_setting(SETTING_APPEARANCE_MODE, mode)

    def _on_color_theme_change(self, choice: str) -> None:
        ctk.set_default_color_theme(choice)
        self.app.db.set_setting(SETTING_COLOR_THEME, choice)
        self.feedback.info(f"Accent set to {choice}. Restart the app to fully apply button colors.")

    def _load_directory_lists(self) -> None:
        self.departments_text.delete("1.0", "end")
        self.departments_text.insert("1.0", "\n".join(self.app.db.list_departments()))

    def _save_directory_lists(self) -> None:
        depts = [line.strip() for line in self.departments_text.get("1.0", "end").splitlines() if line.strip()]
        try:
            self.app.db.set_departments(depts)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success("Department list saved.")
        self._load_directory_lists()

    def _import_directory_lists(self) -> None:
        new_clients, new_depts = self.app.db.import_directory_from_data()
        self._load_directory_lists()
        self.feedback.success(
            f"Imported {new_clients} client company name(s) and {new_depts} department(s) from existing data."
        )

    def _refresh_pricing_services(self) -> None:
        services = self.app.db.list_pricing_service_types()
        if not services:
            services = [PRICING_DEFAULT_SERVICE]
        self.pricing_service_menu.configure(values=services)
        current = self.pricing_service_menu.get()
        if current not in services:
            self.pricing_service_menu.set(services[0])

    def _configure_pricing_form_for_service(self, service_type: str) -> None:
        uses_ranges = pricing_uses_transaction_ranges(service_type)
        if uses_ranges:
            self.pricing_tree.tree.heading("range", text="Transaction range")
            self.pricing_range_heading.configure(text="Transaction range")
            self.pricing_range_menu.grid(row=0, column=1, sticky="w", pady=4)
            self.pricing_charge_entry.grid_remove()
            self.pricing_add_charge_btn.grid_remove()
            self.pricing_delete_charge_btn.grid_remove()
            self.pricing_monthly_label.configure(text="Monthly fee (THB)")
            self.pricing_annual_entry.grid(row=1, column=1, sticky="w", pady=4)
            self.pricing_headcount_entry.grid(row=2, column=1, sticky="w", pady=4)
        else:
            self.pricing_tree.tree.heading("range", text="Charge line")
            self.pricing_range_heading.configure(text="Charge line")
            self.pricing_range_menu.grid_remove()
            self.pricing_charge_entry.grid(row=0, column=1, sticky="w", pady=4)
            self.pricing_add_charge_btn.grid()
            self.pricing_delete_charge_btn.grid()
            self.pricing_monthly_label.configure(text="Fee (THB)")
            self.pricing_annual_entry.grid_remove()
            self.pricing_headcount_entry.grid_remove()
            self.pricing_annual_var.set("")
            self.pricing_headcount_var.set("")

    def _refresh_pricing_matrix(self) -> None:
        service_type = self.pricing_service_menu.get().strip() or PRICING_DEFAULT_SERVICE
        self._configure_pricing_form_for_service(service_type)
        rows = self.app.db.get_pricing_matrix(service_type=service_type)
        self._pricing_rows = {str(row["id"]): row for row in rows}
        tree_rows = [
            (
                row.get("transaction_range") or "",
                f"{(row.get('monthly_fee') or 0):,}",
                f"{(row.get('annual_fee') or 0):,}",
                str(row.get("sla_hours") or ""),
                str(row.get("headcount") or ""),
                row.get("required_docs") or "",
            )
            for row in rows
        ]
        self.pricing_tree.set_rows(tree_rows, iids=[str(row["id"]) for row in rows])
        if rows:
            first = str(rows[0]["id"])
            self.pricing_tree.tree.selection_set(first)
            self.pricing_tree.tree.focus(first)
            self._on_pricing_row_select(first)

    def _on_pricing_service_change(self, _choice: str) -> None:
        self._refresh_pricing_matrix()

    def _on_pricing_row_select(self, iid: str | None) -> None:
        if not iid:
            self._selected_pricing_id = None
            return
        row = self._pricing_rows.get(str(iid))
        if not row:
            self._selected_pricing_id = None
            return
        self._selected_pricing_id = int(iid)
        self._load_pricing_tier(row.get("transaction_range") or "")

    def _load_pricing_tier(self, transaction_range: str) -> None:
        service_type = self.pricing_service_menu.get().strip() or PRICING_DEFAULT_SERVICE
        self._configure_pricing_form_for_service(service_type)
        tier = self.app.db.lookup_pricing_by_range(transaction_range, service_type=service_type)
        self.pricing_range_var.set(transaction_range)
        self.pricing_monthly_var.set(str(tier.get("monthly_fee") or "") if tier else "")
        self.pricing_annual_var.set(str(tier.get("annual_fee") or "") if tier else "")
        self.pricing_sla_var.set(str(tier.get("sla_hours") or "") if tier else "")
        self.pricing_headcount_var.set(str(tier.get("headcount") or "") if tier else "")
        self.pricing_docs_var.set(str(tier.get("required_docs") or "") if tier else "")
        if tier:
            self._selected_pricing_id = int(tier["id"])

    def _reset_service_pricing(self) -> None:
        service_type = self.pricing_service_menu.get().strip() or PRICING_DEFAULT_SERVICE
        uses_ranges = pricing_uses_transaction_ranges(service_type)
        label = "transaction tiers" if uses_ranges else "charge lines"
        if not messagebox.askyesno(
            "Reset pricing",
            f"Reset all {label} for '{service_type}' to defaults?",
            parent=self.winfo_toplevel(),
        ):
            return
        self.app.db.reset_service_pricing_to_defaults(service_type)
        self.feedback.success(f"Pricing reset for {service_type}.")
        self._refresh_pricing_matrix()

    def _seed_all_service_pricing(self) -> None:
        self.app.db._seed_all_service_pricing()
        self._refresh_pricing_services()
        self._refresh_pricing_matrix()
        self.feedback.success("Pricing tiers ensured for all services.")

    def _save_pricing_tier(self) -> None:
        service_type = self.pricing_service_menu.get().strip() or PRICING_DEFAULT_SERVICE
        uses_ranges = pricing_uses_transaction_ranges(service_type)
        transaction_range = self.pricing_range_var.get().strip()
        if not transaction_range:
            label = "transaction range" if uses_ranges else "charge line"
            self.feedback.error(f"Enter a {label} first.")
            return

        def _parse_int(value: str, label: str) -> int | None:
            raw = value.strip()
            if not raw:
                return None
            try:
                return int(raw.replace(",", ""))
            except ValueError as exc:
                raise ValueError(f"{label} must be a whole number.") from exc

        try:
            fee_label = "Fee" if not uses_ranges else "Monthly fee"
            monthly = _parse_int(self.pricing_monthly_var.get(), fee_label)
            annual = _parse_int(self.pricing_annual_var.get(), "Annual fee") if uses_ranges else 0
            sla = _parse_int(self.pricing_sla_var.get(), "SLA hours")
            headcount = _parse_int(self.pricing_headcount_var.get(), "Headcount") if uses_ranges else 0
        except ValueError as exc:
            self.feedback.error(str(exc))
            return

        docs = self.pricing_docs_var.get().strip() or None
        selected_id = getattr(self, "_selected_pricing_id", None)
        tier = (
            self.app.db.get_pricing_tier(int(selected_id))
            if selected_id
            else self.app.db.lookup_pricing_by_range(transaction_range, service_type=service_type)
        )
        try:
            if tier:
                self.app.db.update_pricing_tier(
                    tier["id"],
                    transaction_range=transaction_range,
                    monthly_fee=monthly,
                    annual_fee=annual,
                    sla_hours=sla,
                    headcount=headcount,
                    required_docs=docs,
                )
            else:
                self.app.db.add_pricing_tier(
                    service_type=service_type,
                    transaction_range=transaction_range,
                    monthly_fee=monthly or 0,
                    annual_fee=annual or 0,
                    sla_hours=sla or 0,
                    headcount=headcount or 0,
                    required_docs=docs or "",
                )
        except Exception as exc:
            self.feedback.error(f"Could not save pricing: {exc}")
            return
        self.feedback.success(f"Pricing saved for {service_type}.")
        self._refresh_pricing_matrix()
        self.app.set_status(f"Pricing updated: {service_type} / {transaction_range}")

    def _add_pricing_charge_line(self) -> None:
        service_type = self.pricing_service_menu.get().strip() or PRICING_DEFAULT_SERVICE
        if pricing_uses_transaction_ranges(service_type):
            self.feedback.error("Charge lines apply only to flat-fee services.")
            return
        name = simpledialog.askstring(
            "New charge line",
            "Charge name (e.g. DBD fee, Registration fee):",
            parent=self.winfo_toplevel(),
        )
        if not name:
            return
        charge_name = name.strip()
        if not charge_name:
            self.feedback.error("Charge line name cannot be empty.")
            return
        if self.app.db.lookup_pricing_by_range(charge_name, service_type=service_type):
            self.feedback.error(f"Charge line '{charge_name}' already exists.")
            return
        try:
            tier_id = self.app.db.add_pricing_tier(
                service_type=service_type,
                transaction_range=charge_name,
                monthly_fee=0,
                annual_fee=0,
                sla_hours=0,
                headcount=0,
                required_docs="",
            )
        except Exception as exc:
            self.feedback.error(f"Could not add charge line: {exc}")
            return
        self.feedback.success(f"Added charge line: {charge_name}")
        self._refresh_pricing_matrix()
        self.pricing_tree.tree.selection_set(str(tier_id))
        self.pricing_tree.tree.focus(str(tier_id))
        self._on_pricing_row_select(str(tier_id))

    def _delete_pricing_charge_line(self) -> None:
        service_type = self.pricing_service_menu.get().strip() or PRICING_DEFAULT_SERVICE
        if pricing_uses_transaction_ranges(service_type):
            self.feedback.error("Charge lines apply only to flat-fee services.")
            return
        selected_id = getattr(self, "_selected_pricing_id", None)
        if not selected_id:
            self.feedback.error("Select a charge line to delete.")
            return
        row = self._pricing_rows.get(str(selected_id))
        if not row:
            self.feedback.error("Select a charge line to delete.")
            return
        charge_name = row.get("transaction_range") or "this charge line"
        if not messagebox.askyesno(
            "Delete charge line",
            f"Delete '{charge_name}' from {service_type}?",
            parent=self.winfo_toplevel(),
        ):
            return
        self.app.db.delete_pricing_tier(int(selected_id))
        self._selected_pricing_id = None
        self.feedback.success(f"Deleted charge line: {charge_name}")
        self._refresh_pricing_matrix()

    def _save_portal(self) -> None:
        try:
            url = normalize_portal_url(self.portal_var.get())
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.app.db.set_setting(SETTING_PORTAL_URL, url)
        self.portal_var.set(url)
        self.feedback.success("Portal URL saved.")

    def _on_language_change(self, lang: str) -> None:
        from skyadmin_pro.services import i18n

        i18n.set_language(lang.lower())
        self.app.db.set_setting("ui_language", lang.lower())
        self.feedback.info(f"Language set to {lang}. Restart the app to fully apply.")

    def _save_tagline(self) -> None:
        from skyadmin_pro.config import APP_TAGLINE, SETTING_APP_TAGLINE

        text = self.tagline_var.get().strip()
        saved = text or APP_TAGLINE
        self.app.db.set_setting(SETTING_APP_TAGLINE, saved)
        self.feedback.success("Tagline saved.")
        self.app.refresh_tagline(saved)
        self.app.set_status(f"Tagline: {saved}")

    def _open_activation(self) -> None:
        from skyadmin_pro.ui.activation import ActivationDialog

        ActivationDialog(
            self,
            allow_quit=False,
            on_activated=self._refresh_license_label,
        )

    def _activate_with_passcode(self) -> None:
        import threading

        from skyadmin_pro.services.license import (
            check_activation_usable,
            fetch_revocations,
            mark_used,
            requires_online_check,
            save_license_file,
        )

        code = " ".join(self.passcode_var.get().split())
        if not code:
            self.feedback.error("Enter a passcode first.")
            return

        self.feedback.info("Verifying passcode…")
        self.configure(cursor="watch")
        self.update_idletasks()

        def worker():
            ok, msg, nonce = check_activation_usable(code)
            if not ok:
                self._after(lambda: self._activation_fail(msg))
                return
            if requires_online_check():
                net_ok, net_msg = fetch_revocations(timeout=6)
                if not net_ok:
                    self._after(
                        lambda: self._activation_fail("Internet required to activate - " + net_msg.splitlines()[0])
                    )
                    return
                ok2, msg2, nonce2 = check_activation_usable(code)
                if not ok2:
                    self._after(lambda: self._activation_fail(msg2))
                    return
                ok, msg, nonce = ok2, msg2, nonce2
            save_license_file(code)
            if nonce:
                mark_used(nonce)
            self._after(lambda: self._activation_ok(msg, "passcode"))

        threading.Thread(target=worker, daemon=True).start()

    def _activate_with_key(self) -> None:
        import threading

        from skyadmin_pro.services.license import (
            check_activation_usable,
            fetch_revocations,
            mark_used,
            requires_online_check,
            save_license_file,
        )

        content = self.key_paste_var.get().strip()
        if not content:
            self.feedback.error("Paste a license key first.")
            return

        self.feedback.info("Verifying license key…")
        self.configure(cursor="watch")
        self.update_idletasks()

        def worker():
            ok, msg, nonce = check_activation_usable(content)
            if not ok:
                self._after(lambda: self._activation_fail(msg))
                return
            if requires_online_check():
                net_ok, net_msg = fetch_revocations(timeout=6)
                if not net_ok:
                    self._after(
                        lambda: self._activation_fail("Internet required to activate - " + net_msg.splitlines()[0])
                    )
                    return
                ok2, msg2, nonce2 = check_activation_usable(content)
                if not ok2:
                    self._after(lambda: self._activation_fail(msg2))
                    return
                ok, msg, nonce = ok2, msg2, nonce2
            save_license_file(content)
            if nonce:
                mark_used(nonce)
            self._after(lambda: self._activation_ok(msg, "key"))

        threading.Thread(target=worker, daemon=True).start()

    def _activation_fail(self, msg) -> None:
        self.configure(cursor="")
        self.feedback.error(msg.splitlines()[0])

    def _activation_ok(self, msg, kind) -> None:
        self.configure(cursor="")
        self.passcode_var.set("")
        self.key_paste_var.set("")
        self._refresh_license_label()
        self.feedback.success(f"✓ {msg.splitlines()[0]} — activated.")
        self.app.set_status(f"License activated via {kind}.")
        self.app.refresh_sidebar_status()

    def _after(self, fn) -> None:
        def wrapped() -> None:
            if not self.winfo_exists():
                return
            fn()

        try:
            self.after(0, wrapped)
        except Exception:
            pass

    def _refresh_license_label(self) -> None:
        try:
            from skyadmin_pro.services.license import (
                get_daily_sync_status,
                get_machine_id,
                license_expiry_text,
                verify_license,
            )

            ok, _msg = verify_license()
            if ok:
                self.license_label.configure(
                    text=f"✓ License active — {license_expiry_text()}  ·  Machine ID: {get_machine_id()}",
                    text_color=("#15803d", "#4ade80"),
                )
            else:
                self.license_label.configure(
                    text=f"✗ No valid license  ·  Machine ID: {get_machine_id()}",
                    text_color=("#b45309", "#fbbf24"),
                )
            # Daily online status
            try:
                sync_ok, sync_msg = get_daily_sync_status()
                self.daily_sync_label.configure(
                    text=("✓ " if sync_ok else "⚠ ") + sync_msg,
                    text_color=("#15803d", "#4ade80") if sync_ok else ("#b45309", "#fbbf24"),
                )
            except Exception:
                self.daily_sync_label.configure(text="")
        except Exception:
            self.license_label.configure(text="License: unavailable")
            try:
                self.daily_sync_label.configure(text="")
            except Exception:
                pass

    def _sync_now(self) -> None:
        import threading

        from skyadmin_pro.services.license import fetch_revocations

        self.feedback.info("Syncing license control list…")
        self.daily_sync_label.configure(text="Syncing…", text_color=TEXT_MUTED)

        def worker():
            ok, msg = fetch_revocations(timeout=6)

            def done():
                if not self.winfo_exists():
                    return
                if ok:
                    self.feedback.success(msg.splitlines()[0])
                else:
                    self.feedback.error(msg.splitlines()[0])
                self._refresh_license_label()
                try:
                    self.app.refresh_sidebar_status()
                    self.app.set_status(msg.splitlines()[0])
                except Exception:
                    pass

            try:
                self.after(0, done)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _show_license(self) -> None:
        # Read from the app itself (embedded) so it always works in the
        # packaged exe; fall back to the shipped LICENSE file if present.
        from skyadmin_pro.config import LEGAL_LICENSE_TEXT

        self._show_legal("License Agreement", LEGAL_LICENSE_TEXT)

    def _show_disclaimer(self) -> None:
        from skyadmin_pro.config import LEGAL_DISCLAIMER_TEXT

        self._show_legal("Disclaimer", LEGAL_DISCLAIMER_TEXT)

    def _show_legal(self, title: str, text: str) -> None:
        top = ctk.CTkToplevel(self)
        top.title(f"SkyAdmin Pro — {title}")
        top.geometry("720x560")
        top.transient(self.winfo_toplevel())
        top.attributes("-topmost", True)
        from skyadmin_pro.ui.widgets import make_modal

        make_modal(top)
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(0, weight=1)
        box = ctk.CTkTextbox(top, wrap="word")
        box.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        box.insert("1.0", text)
        box.configure(state="disabled")
        ctk.CTkButton(top, text="Close", width=110, command=top.destroy).grid(row=1, column=0, pady=(0, 16))
