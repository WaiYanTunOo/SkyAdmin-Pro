"""Dashboard jumps open the menu page that owns the work."""

from __future__ import annotations

from skyadmin_pro.config import NAV_DATABASE_TASKS, NAV_PIPELINE, NAV_SUPPLIERS, NAV_TASKS, NAV_TAX_STATUS
from skyadmin_pro.ui.views.database_tasks.view.funcs import open_menu_view

from .jumps_companies import (  # noqa: F401 — re-export for card commands
    open_calendar_tab,
    open_clients_tab,
    open_company_details_tab,
    open_expiry,
    open_filing_statuses,
    open_money_tab,
    open_vo_csh_setup,
)


def follow_next(app, kind: str, value: str, iid: str) -> None:
    if kind == "task":
        task_id = _int_id(value) or _int_id(iid.split("-", 1)[-1] if "-" in iid else "")
        if task_id is None:
            app.show_view(NAV_TASKS)
        else:
            open_menu_view(app, NAV_TASKS, "open_task", task_id)
        return
    if kind == "pipeline":
        open_pipeline(app, value)
        return
    if kind == "supplier":
        app.show_view(NAV_SUPPLIERS)
        return
    if kind == "renewal":
        _companies(app, "open_renewal", value)
        return
    if kind == "company" and value:
        _companies(app, "open_company_details", value)


def open_pipeline(app, item_id: str = "") -> None:
    parsed = _int_id(item_id)
    view = app._ensure_view(NAV_PIPELINE)
    if view is not None and parsed is not None:
        view.panel._page = 0
        view.panel._pending_select = parsed
    app.show_view(NAV_PIPELINE)


def open_company(app, name: str) -> None:
    if name:
        _companies(app, "open_company_details", name)
    else:
        open_company_details_tab(app)


def open_tax_status(app) -> None:
    app.show_view(NAV_TAX_STATUS)


def open_suppliers(app) -> None:
    app.show_view(NAV_SUPPLIERS)


def _companies(app, method: str, value: str) -> None:
    if value:
        from .jumps_companies import _call_companies

        _call_companies(app, method, value)
    else:
        app.show_view(NAV_DATABASE_TASKS)


def _int_id(raw: str) -> int | None:
    text = str(raw or "").strip()
    return int(text) if text.isdigit() else None
