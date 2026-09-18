from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import PRICING_DEFAULT_SERVICE
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import SectionCard


class SettingsViewMixin3:
    def _build_business_tab_pricing(self, tab) -> None:
        """Toolbar + pricing_tree on tab (outside CanvasScrollFrame)."""
        pricing = SectionCard(
            tab,
            title="Client fee matrix",
            subtitle=(
                "What this firm charges a client. Not the license price list. "
                "Accounting uses transaction-volume tiers; other services use named charge lines."
            ),
        )
        pricing.grid(row=0, column=0, sticky="ew", pady=(0, 8))
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
            tab,
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
        self.pricing_tree.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
