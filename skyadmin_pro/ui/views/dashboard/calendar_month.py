"""Month header + panel shell for Dashboard Calendar."""

from __future__ import annotations

from datetime import date

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_BG, CARD_RADIUS, FONT_SIZE_MD, FONT_SIZE_SM, TEXT_MUTED


def step_month(d: date, delta: int) -> date:
    total = d.year * 12 + (d.month - 1) + delta
    return date(total // 12, total % 12 + 1, 1)


def build_month_panel(view, parent) -> None:
    card = ctk.CTkFrame(parent, corner_radius=CARD_RADIUS, fg_color=CARD_BG)
    card.grid(row=0, column=0, sticky="nsew")
    card.grid_columnconfigure(0, weight=1)
    card.grid_rowconfigure(1, weight=1)
    _nav(view, card)
    view._calendar_grid = ctk.CTkFrame(card, fg_color="transparent")
    view._calendar_grid.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
    for col in range(7):
        view._calendar_grid.grid_columnconfigure(col, weight=1, uniform="cal")
    view._calendar_grid.grid_rowconfigure(0, weight=0)
    for row in range(1, 7):
        view._calendar_grid.grid_rowconfigure(row, weight=1, uniform="calrow", minsize=56)


def _nav(view, card) -> None:
    nav = ctk.CTkFrame(card, fg_color="transparent")
    nav.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 8))
    nav.grid_columnconfigure(1, weight=1)
    ctk.CTkButton(nav, text="\u25c0", width=32, command=lambda: shift_month(view, -1)).grid(row=0, column=0, sticky="w")
    view.calendar_month_label = ctk.CTkLabel(
        nav, text="", font=ctk.CTkFont(size=FONT_SIZE_MD, weight="bold"), anchor="center"
    )
    view.calendar_month_label.grid(row=0, column=1, sticky="ew", padx=8)
    right = ctk.CTkFrame(nav, fg_color="transparent")
    right.grid(row=0, column=2, sticky="e")
    view.calendar_count_label = ctk.CTkLabel(
        right,
        text="",
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=FONT_SIZE_SM),
        anchor="e",
    )
    view.calendar_count_label.pack(side="left", padx=(0, 10))
    ctk.CTkButton(right, text="Today", width=64, command=lambda: go_today(view)).pack(side="left", padx=(0, 6))
    ctk.CTkButton(right, text="\u25b6", width=32, command=lambda: shift_month(view, 1)).pack(side="left")


def shift_month(view, delta: int) -> None:
    cur = getattr(view, "_calendar_month", date.today().replace(day=1))
    view._calendar_month = step_month(cur, delta)
    from .calendar_actions import redraw_month

    redraw_month(view)


def go_today(view) -> None:
    today = date.today()
    from .calendar_actions import select_calendar_day

    # Same-month: paint selection only; month change triggers redraw_month.
    select_calendar_day(view, today, redraw=False)
