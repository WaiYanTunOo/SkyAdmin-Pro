"""Dashboard jumps open the menu page that owns the work."""

from __future__ import annotations

from skyadmin_pro.config import NAV_DATABASE_TASKS, NAV_PIPELINE, NAV_SUPPLIERS, NAV_TASKS, NAV_TAX_STATUS
from skyadmin_pro.ui.views.database_tasks.view.funcs import open_menu_view


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
        app.show_view(NAV_DATABASE_TASKS)


def open_tax_status(app) -> None:
    app.show_view(NAV_TAX_STATUS)


def open_suppliers(app) -> None:
    app.show_view(NAV_SUPPLIERS)


def _companies(app, method: str, value: str) -> None:
    view = app._ensure_view(NAV_DATABASE_TASKS)
    app.show_view(NAV_DATABASE_TASKS)
    opener = getattr(view, method, None) if view is not None else None
    if callable(opener) and value:
        opener(value)


def _int_id(raw: str) -> int | None:
    text = str(raw or "").strip()
    return int(text) if text.isdigit() else None
