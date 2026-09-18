"""Month close and tax overview as a count plus Open — not embedded trees."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_TITLE_SIZE, TEXT_MUTED

from .jumps import open_tax_status
from .month_host import MonthCloseHost


def build_money_lines(view) -> None:
    view._detail_stage = 1
    month = ctk.CTkFrame(view._money, corner_radius=12)
    month.grid(row=0, column=0, sticky="ew", pady=(0, 12))
    month.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(month, text="Month close", font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"), anchor="w").grid(
        row=0, column=0, sticky="w", padx=16, pady=14
    )
    month_count = ctk.CTkLabel(month, text="—", text_color=TEXT_MUTED, anchor="w")
    month_count.grid(row=0, column=1, sticky="w", padx=(8, 8), pady=14)
    view.month_panel = MonthCloseHost(view.app, month_count)
    ctk.CTkButton(month, text="Open", width=90, command=lambda: open_tax_status(view.app)).grid(
        row=0, column=2, sticky="e", padx=(0, 16), pady=14
    )

    tax = ctk.CTkFrame(view._money, corner_radius=12)
    tax.grid(row=1, column=0, sticky="ew", pady=(0, 12))
    tax.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(tax, text="Tax overview", font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"), anchor="w").grid(
        row=0, column=0, sticky="w", padx=16, pady=14
    )
    view.tax_count_label = ctk.CTkLabel(tax, text="—", text_color=TEXT_MUTED, anchor="w")
    view.tax_count_label.grid(row=0, column=1, sticky="w", padx=(8, 8), pady=14)
    actions = ctk.CTkFrame(tax, fg_color="transparent")
    actions.grid(row=0, column=2, sticky="e", padx=(0, 16), pady=10)
    ctk.CTkButton(
        actions, text="Run Monthly Cycle", width=150, fg_color=("#15803d", "#16a34a"), command=view._run_monthly_cycle
    ).pack(side="left")
    ctk.CTkButton(
        actions,
        text="Accounting setup",
        width=130,
        fg_color="transparent",
        border_width=1,
        command=view._open_accounting_setup,
    ).pack(side="left", padx=(8, 0))
    ctk.CTkButton(
        actions,
        text="VO/CSH setup",
        width=110,
        fg_color="transparent",
        border_width=1,
        command=view._open_vo_csh_setup,
    ).pack(side="left", padx=(8, 0))
    ctk.CTkButton(actions, text="Open", width=80, command=view._open_accounting_setup).pack(side="left", padx=(8, 0))
