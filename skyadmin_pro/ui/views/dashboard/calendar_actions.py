"""Calendar tab load / select helpers (month grid + day popup)."""

from __future__ import annotations

import calendar as cal
from datetime import date


def _visible_range(month: date) -> tuple[str, str]:
    weeks = cal.Calendar(firstweekday=cal.MONDAY).monthdatescalendar(month.year, month.month)
    return weeks[0][0].isoformat(), weeks[-1][-1].isoformat()


def load_month_appointments(view) -> None:
    month = getattr(view, "_calendar_month", date.today().replace(day=1))
    from_date, to_date = _visible_range(month)
    rows = view.app.db.list_appointments(from_date=from_date, to_date=to_date, limit=500)
    by_day: dict[str, list] = {}
    rows_by_id: dict[str, dict] = {}
    for r in rows:
        key = str(r.get("appt_date") or "")[:10]
        by_day.setdefault(key, []).append(r)
        rows_by_id[str(r["id"])] = r
    view._calendar_by_day = by_day
    view._calendar_rows = rows_by_id


def redraw_month(view) -> None:
    load_month_appointments(view)
    from .calendar_grid import redraw_month_grid

    redraw_month_grid(view)
    _refresh_day_list_if_open(view)


def _refresh_day_list_if_open(view) -> None:
    if getattr(view, "_calendar_popup", None) is None:
        return
    from .calendar_detail import refresh_day_list

    refresh_day_list(view)


def on_day_click(view, day: date) -> None:
    # Selection only — popup open rebuilds the day list; avoid full month destroy.
    select_calendar_day(view, day, redraw=False)
    from .calendar_popup import open_day_popup

    open_day_popup(view, day)


def on_appt_chip(view, appt: dict) -> None:
    day_s = str(appt.get("appt_date") or "")[:10]
    day = getattr(view, "_calendar_selected_day", date.today())
    if day_s:
        try:
            day = date.fromisoformat(day_s)
        except ValueError:
            pass
    select_calendar_day(view, day, redraw=False)
    from .calendar_popup import open_day_popup

    open_day_popup(view, day, appt_id=appt.get("id"))


def select_calendar_day(view, day: date, *, redraw: bool = False) -> None:
    previous = getattr(view, "_calendar_selected_day", None)
    old_month = getattr(view, "_calendar_month", None)
    view._calendar_selected_day = day
    view._calendar_month = day.replace(day=1)
    view._selected_appointment_id = None
    if redraw or view._calendar_month != old_month:
        redraw_month(view)
        return
    from .calendar_select import paint_selection

    paint_selection(view, previous)


def update_calendar_count(view, snap: dict | None = None) -> None:
    label = getattr(view, "calendar_count_label", None)
    if label is None:
        return
    if snap is not None and "upcoming_appointments" in snap:
        n = int(snap.get("upcoming_appointments") or 0)
    else:
        n = view.app.db.count_upcoming_appointments(30)
    try:
        label.configure(text=f"{n} upcoming (30 days)")
    except Exception:
        pass
