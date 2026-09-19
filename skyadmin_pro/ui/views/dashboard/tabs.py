"""In-page Dashboard tabs. One page, no new sidebar item."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import NAV_SUPPLIERS, NAV_TASKS
from skyadmin_pro.ui.canvas_scroll import CanvasScrollFrame
from skyadmin_pro.ui.theme import SURFACE_BG
from skyadmin_pro.ui.widgets import themed_tabview

from .jumps import (
    open_clients_tab,
    open_company_details_tab,
    open_expiry,
    open_filing_statuses,
    open_money_tab,
    open_pipeline,
    open_vo_csh_setup,
)


def install_tabs(view) -> None:
    tabs = themed_tabview(view._detail, command=lambda: _on_tab_change(view))
    tabs.grid(row=0, column=0, sticky="nsew")
    view._dash_tabs = tabs
    today_tab = tabs.add("Today")
    view._money = tabs.add("Money")
    view._incentive = tabs.add("Incentive")
    view._calendar = tabs.add("Calendar")
    view._calendar_built = False
    for name in ("Today", "Money", "Incentive", "Calendar"):
        tabs.tab(name).configure(fg_color=SURFACE_BG)
    today_tab.grid_columnconfigure(0, weight=1)
    today_tab.grid_rowconfigure(0, weight=1)
    view._detail_scroll = CanvasScrollFrame(today_tab)
    view._detail_scroll.grid(row=0, column=0, sticky="nsew")
    view._detail_scroll.content.grid_columnconfigure(0, weight=1)
    view._today = view._detail_scroll.content
    view._money.grid_columnconfigure(0, weight=1)
    view._incentive.grid_columnconfigure(0, weight=1)
    view._incentive.grid_rowconfigure(0, weight=1)
    view._calendar.grid_columnconfigure(0, weight=3)
    view._calendar.grid_columnconfigure(1, weight=2)
    view._calendar.grid_rowconfigure(1, weight=1)
    _stat_cards(view)


def _on_tab_change(view) -> None:
    try:
        view._detail_scroll._on_content_configure()
    except Exception as e:
        import logging

        logging.error(f"UI Error: {e}")
    tabs = getattr(view, "_dash_tabs", None)
    if tabs is not None and tabs.get() == "Calendar":
        from .calendar_tab import ensure_calendar

        ensure_calendar(view)


def _stat_cards(view) -> None:
    view._row1 = ctk.CTkFrame(view._today, fg_color="transparent")
    view._row1.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    for i in range(5):
        view._row1.grid_columnconfigure(i, weight=1)
    view.card_pending = view._stat_card(view._row1, 0, "Pending tasks", "0", lambda: view.app.show_view(NAV_TASKS))
    view.card_done = view._stat_card(view._row1, 1, "Completed today", "0", lambda: view.app.show_view(NAV_TASKS))
    view.card_expiring = view._stat_card(view._row1, 2, "Expiry alerts", "0", lambda: open_expiry(view.app))
    view.card_overdue = view._stat_card(
        view._row1, 3, "Overdue payments", "0", lambda: open_company_details_tab(view.app)
    )
    view.card_clients = view._stat_card(view._row1, 4, "Clients", "0", lambda: open_clients_tab(view.app))
    view._row2 = ctk.CTkFrame(view._today, fg_color="transparent")
    view._row2.grid(row=1, column=0, sticky="ew", pady=(0, 12))
    for i in range(5):
        view._row2.grid_columnconfigure(i, weight=1)
    view.card_supplier = view._stat_card(view._row2, 0, "Supplier due", "0", lambda: view.app.show_view(NAV_SUPPLIERS))
    view.card_ongoing = view._stat_card(view._row2, 1, "Ongoing services", "0", lambda: open_pipeline(view.app))
    view.card_pending_filings = view._stat_card(
        view._row2, 2, "Tax filings pending", "0", lambda: open_filing_statuses(view.app)
    )
    view.card_revenue = view._stat_card(view._row2, 3, "Monthly revenue", "0", lambda: open_money_tab(view))
    view.card_vo_csh = view._stat_card(view._row2, 4, "VO/CSH expiring", "0", lambda: open_vo_csh_setup(view.app))
