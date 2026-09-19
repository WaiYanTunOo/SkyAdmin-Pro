"""Dashboard Calendar tab — full-width month grid (day edit via popup)."""

from __future__ import annotations

from datetime import date

from .calendar_month import build_month_panel


def ensure_calendar(view) -> None:
    """Lazy-build Calendar tab on first visit."""
    if getattr(view, "_calendar_built", False):
        return
    host = getattr(view, "_calendar", None)
    if host is None:
        return
    view._calendar_built = True
    view._selected_appointment_id = None
    view._calendar_popup = None
    today = date.today()
    view._calendar_month = today.replace(day=1)
    view._calendar_selected_day = today
    # Single full-width column — no nested scroll host.
    host.grid_columnconfigure(0, weight=1)
    host.grid_columnconfigure(1, weight=0)
    host.grid_rowconfigure(0, weight=1)
    host.grid_rowconfigure(1, weight=0)
    build_month_panel(view, host)
    refresh_calendar(view)


def refresh_calendar(view, snap: dict | None = None, *, reload_grid: bool = True) -> None:
    """Refresh calendar count and optionally the month grid.

    Dashboard snapshot applies use reload_grid=False so poll/refresh_async only
    updates the upcoming-count label; mutate/ensure/month-step pass True (default).
    """
    if not getattr(view, "_calendar_built", False):
        return
    from .calendar_actions import redraw_month, update_calendar_count

    if reload_grid:
        redraw_month(view)
    update_calendar_count(view, snap)
