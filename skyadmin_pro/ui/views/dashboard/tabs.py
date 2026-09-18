"""In-page Dashboard tabs. One page, no new sidebar item."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import SURFACE_BG
from skyadmin_pro.ui.widgets import themed_tabview


def install_tabs(view) -> None:
    tabs = themed_tabview(view._detail, command=lambda: view._detail_scroll._on_content_configure())
    tabs.grid(row=0, column=0, sticky="ew")
    view._dash_tabs = tabs
    view._today = tabs.add("Today")
    view._money = tabs.add("Money")
    view._incentive = tabs.add("Incentive")
    for name, frame in (("Today", view._today), ("Money", view._money), ("Incentive", view._incentive)):
        tabs.tab(name).configure(fg_color=SURFACE_BG)
        frame.grid_columnconfigure(0, weight=1)
    _stat_cards(view)


def _stat_cards(view) -> None:
    view._row1 = ctk.CTkFrame(view._today, fg_color="transparent")
    view._row1.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    for i in range(5):
        view._row1.grid_columnconfigure(i, weight=1)
    from skyadmin_pro.config import (
        NAV_DASHBOARD,
        NAV_DATABASE_TASKS,
        NAV_PIPELINE,
        NAV_SUPPLIERS,
        NAV_TASKS,
        NAV_TAX_STATUS,
    )

    view.card_pending = view._stat_card(view._row1, 0, "Pending tasks", "0", lambda: view.app.show_view(NAV_TASKS))
    view.card_done = view._stat_card(view._row1, 1, "Completed today", "0", lambda: view.app.show_view(NAV_TASKS))
    view.card_expiring = view._stat_card(
        view._row1, 2, "Expiry alerts", "0", lambda: view.app.show_view(NAV_DATABASE_TASKS)
    )
    view.card_overdue = view._stat_card(
        view._row1, 3, "Overdue payments", "0", lambda: view.app.show_view(NAV_SUPPLIERS)
    )
    view.card_clients = view._stat_card(view._row1, 4, "Clients", "0", lambda: view.app.show_view(NAV_DATABASE_TASKS))

    view._row2 = ctk.CTkFrame(view._today, fg_color="transparent")
    view._row2.grid(row=1, column=0, sticky="ew", pady=(0, 12))
    for i in range(5):
        view._row2.grid_columnconfigure(i, weight=1)
    view.card_supplier = view._stat_card(view._row2, 0, "Supplier due", "0", lambda: view.app.show_view(NAV_SUPPLIERS))
    view.card_ongoing = view._stat_card(
        view._row2, 1, "Ongoing services", "0", lambda: view.app.show_view(NAV_PIPELINE)
    )
    view.card_pending_filings = view._stat_card(
        view._row2, 2, "Tax filings pending", "0", lambda: view.app.show_view(NAV_TAX_STATUS)
    )
    view.card_revenue = view._stat_card(
        view._row2, 3, "Monthly revenue", "0", lambda: view.app.show_view(NAV_DASHBOARD)
    )
    view.card_vo_csh = view._stat_card(
        view._row2, 4, "VO/CSH expiring", "0", lambda: view.app.show_view(NAV_DATABASE_TASKS)
    )
