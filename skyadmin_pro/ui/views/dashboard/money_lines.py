"""Money tab: Monthly Service Close + Tax overview (one purpose per card)."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import (
    ACCENT,
    CARD_BG,
    CARD_RADIUS,
    CARD_TITLE_SIZE,
    FONT_SIZE_SM,
    SECTION_GAP,
    STAT_SUCCESS,
    TEXT_MUTED,
    TEXT_SUBTLE,
)

from .jumps import open_filing_statuses, open_tax_status
from .month_host import MonthCloseHost


def build_money_lines(view) -> None:
    view._detail_stage = 1
    view._money.grid_columnconfigure(0, weight=1)
    _month_close_card(view)
    _tax_overview_card(view)


def _month_close_card(view) -> None:
    card = ctk.CTkFrame(view._money, corner_radius=CARD_RADIUS, fg_color=CARD_BG)
    card.grid(row=0, column=0, sticky="ew", pady=(0, SECTION_GAP))
    card.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(
        card,
        text="Monthly Service Close",
        font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        anchor="w",
    ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 4))
    ctk.CTkLabel(
        card,
        text="Clients whose month is still Open or In progress",
        text_color=TEXT_SUBTLE,
        font=ctk.CTkFont(size=FONT_SIZE_SM),
        anchor="w",
    ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 8))
    row = ctk.CTkFrame(card, fg_color="transparent")
    row.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))
    row.grid_columnconfigure(0, weight=1)
    month_count = ctk.CTkLabel(row, text="—", text_color=TEXT_MUTED, anchor="w")
    month_count.grid(row=0, column=0, sticky="w")
    view.month_panel = MonthCloseHost(view.app, month_count)
    ctk.CTkButton(row, text="Open", width=96, command=lambda: open_tax_status(view.app)).grid(
        row=0, column=1, sticky="e"
    )


def _tax_overview_card(view) -> None:
    card = ctk.CTkFrame(view._money, corner_radius=CARD_RADIUS, fg_color=CARD_BG)
    card.grid(row=1, column=0, sticky="ew", pady=(0, SECTION_GAP))
    card.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(
        card,
        text="Tax overview",
        font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        anchor="w",
    ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 4))
    view.tax_count_label = ctk.CTkLabel(
        card, text="—", text_color=TEXT_MUTED, font=ctk.CTkFont(size=FONT_SIZE_SM), anchor="w"
    )
    view.tax_count_label.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 12))

    primary = ctk.CTkFrame(card, fg_color="transparent")
    primary.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 8))
    ctk.CTkButton(
        primary,
        text="Run Monthly Cycle",
        width=160,
        fg_color=STAT_SUCCESS,
        hover_color=("#166534", "#15803d"),
        command=view._run_monthly_cycle,
    ).pack(side="left")
    ctk.CTkButton(
        primary,
        text="Filing Statuses",
        width=130,
        fg_color=ACCENT,
        command=lambda: open_filing_statuses(view.app),
    ).pack(side="left", padx=(10, 0))

    links = ctk.CTkFrame(card, fg_color="transparent")
    links.grid(row=3, column=0, sticky="w", padx=18, pady=(0, 16))
    for text, cmd in (
        ("Accounting setup", view._open_accounting_setup),
        ("VO/CSH setup", view._open_vo_csh_setup),
        ("Monthly Service Close", lambda: open_tax_status(view.app)),
    ):
        ctk.CTkButton(
            links,
            text=text,
            width=0,
            height=28,
            fg_color="transparent",
            text_color=TEXT_MUTED,
            hover_color=("gray85", "gray25"),
            command=cmd,
        ).pack(side="left", padx=(0, 12))
