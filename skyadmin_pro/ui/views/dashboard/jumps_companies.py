"""Companies-tab jump helpers used by Dashboard cards."""

from __future__ import annotations

from skyadmin_pro.config import NAV_DATABASE_TASKS


def open_expiry(app) -> None:
    _call_companies(app, "open_expiry")


def open_clients_tab(app) -> None:
    _call_companies(app, "open_clients_tab")


def open_company_details_tab(app) -> None:
    _call_companies(app, "open_company_details_tab")


def open_filing_statuses(app) -> None:
    _call_companies(app, "open_filing_statuses")


def open_vo_csh_setup(app) -> None:
    opener = getattr(app, "open_vo_csh_setup", None)
    if callable(opener):
        opener()
    else:
        app.show_view(NAV_DATABASE_TASKS)


def open_money_tab(view) -> None:
    tabs = getattr(view, "_dash_tabs", None)
    if tabs is not None:
        tabs.set("Money")


def open_calendar_tab(view) -> None:
    tabs = getattr(view, "_dash_tabs", None)
    if tabs is not None:
        tabs.set("Calendar")
        from .calendar_tab import ensure_calendar

        ensure_calendar(view)


def _call_companies(app, method: str, *args) -> None:
    view = app._ensure_view(NAV_DATABASE_TASKS)
    app.show_view(NAV_DATABASE_TASKS)
    opener = getattr(view, method, None) if view is not None else None
    if callable(opener):
        opener(*args)
