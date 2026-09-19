"""Form clear / load helpers for Dashboard Calendar day popup."""

from __future__ import annotations

from datetime import date
from tkinter import TclError

from .calendar_time import clear_time_ui, set_time_ui


def _alive(widget) -> bool:
    try:
        return bool(widget is not None and widget.winfo_exists())
    except (TclError, AttributeError):
        return False


def popup_form_ready(view) -> bool:
    """True when the day-popup form widgets still exist."""
    if not _alive(getattr(view, "_calendar_popup", None)):
        return False
    if not all(hasattr(view, n) for n in ("cal_title", "cal_date", "cal_location")):
        return False
    for name in ("cal_hour_entry", "cal_minute_entry", "cal_client_field", "cal_notes_field"):
        obj = getattr(view, name, None)
        if name.endswith("_field"):
            if obj is None or not _alive(getattr(obj, "widget", None)):
                return False
        elif not _alive(obj):
            return False
    return True


def field_get(field, default: str = "") -> str:
    try:
        return field.get() if field is not None else default
    except (TclError, AttributeError, Exception):
        return default


def sync_date_label(view) -> None:
    day = getattr(view, "_calendar_selected_day", None) or date.today()
    iso = day.isoformat() if isinstance(day, date) else str(day)[:10]
    if hasattr(view, "cal_date"):
        try:
            view.cal_date.set(iso)
        except (TclError, AttributeError):
            pass
    lbl = getattr(view, "calendar_date_label", None)
    if lbl is None:
        return
    text = f"Date fixed  ·  {day.strftime('%d %b %Y')}" if isinstance(day, date) else f"Date fixed  ·  {iso}"
    try:
        lbl.configure(text=text)
    except (TclError, AttributeError):
        pass


def clear_appointment_form(view) -> None:
    view._selected_appointment_id = None
    if not popup_form_ready(view):
        return
    day = getattr(view, "_calendar_selected_day", None) or date.today()
    try:
        view.cal_title.set("")
        view.cal_date.set(day.isoformat() if isinstance(day, date) else str(day)[:10])
        clear_time_ui(view)
        view.cal_client_field.set("")
        view.cal_location.set("")
        view.cal_notes_field.clear()
        sync_date_label(view)
    except (TclError, AttributeError):
        return


def load_appointment_into_form(view, iid: str | None) -> None:
    if not iid or not popup_form_ready(view):
        return
    row = (getattr(view, "_calendar_rows", {}) or {}).get(str(iid))
    if row is None:
        row = view.app.db.get_appointment(int(iid))
    if not row:
        return
    view._selected_appointment_id = int(row["id"])
    try:
        view.cal_title.set(row.get("title") or "")
        appt_date = row.get("appt_date") or date.today().isoformat()
        view.cal_date.set(appt_date)
        try:
            view._calendar_selected_day = date.fromisoformat(str(appt_date)[:10])
        except ValueError:
            pass
        set_time_ui(view, row.get("appt_time"))
        view.cal_client_field.set(row.get("client_name") or "")
        view.cal_location.set(row.get("location") or "")
        view.cal_notes_field.set(row.get("notes") or "")
        sync_date_label(view)
    except (TclError, AttributeError):
        return


def drop_form_refs(view) -> None:
    view._cal_hour = None
    view._cal_minute = 0
    for name in (
        "cal_hour_entry",
        "cal_minute_entry",
        "cal_hour_var",
        "cal_minute_var",
        "cal_client_field",
        "cal_notes_field",
        "calendar_date_label",
        "_calendar_day_list",
    ):
        if hasattr(view, name):
            setattr(view, name, None)
