from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import TRANSACTION_RANGES
from skyadmin_pro.ui.widgets import SectionCard, themed_entry, themed_textbox


class SettingsViewMixin4:
    def _build_business_tab_pricing_form(self, pricing_body):
        pricing_form = ctk.CTkFrame(pricing_body, fg_color="transparent")
        pricing_form.grid(row=2, column=0, sticky="ew")
        pricing_form.grid_columnconfigure((1, 3), weight=1, uniform="fee_field")
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

    def _build_business_tab_services(self, scroll, row: int) -> int:
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
        return row + 1
