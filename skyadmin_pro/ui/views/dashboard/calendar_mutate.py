"""Calendar appointment save / delete."""

from __future__ import annotations

from datetime import date
from tkinter import TclError, messagebox

from .calendar_form_state import clear_appointment_form, field_get, popup_form_ready
from .calendar_tab import refresh_calendar
from .calendar_time import get_stored_time


def _parent(view):
    top = getattr(view, "_calendar_popup", None)
    try:
        if top is not None and top.winfo_exists():
            return top
    except (TclError, AttributeError):
        pass
    return view.winfo_toplevel()


def save_appointment(view) -> None:
    parent = _parent(view)
    if not popup_form_ready(view):
        return
    try:
        title = view.cal_title.get().strip()
        appt_date = view.cal_date.get().strip()
        location = view.cal_location.get().strip() or None
    except (TclError, AttributeError):
        return
    if not title:
        messagebox.showerror("Appointment", "Title is required.", parent=parent)
        return
    if not appt_date:
        messagebox.showerror("Appointment", "Date is required.", parent=parent)
        return
    appt_time = get_stored_time(view)
    client_name = field_get(view.cal_client_field)
    client_id = view.app.db.client_id_by_name(client_name) if client_name else None
    fields = {
        "title": title,
        "appt_date": appt_date,
        "appt_time": appt_time,
        "client_id": client_id,
        "location": location,
        "notes": field_get(view.cal_notes_field) or None,
    }
    appt_id = getattr(view, "_selected_appointment_id", None)
    if appt_id:
        view.app.db.update_appointment(appt_id, **fields)
    else:
        view._selected_appointment_id = view.app.db.add_appointment(**fields)
    try:
        view._calendar_selected_day = date.fromisoformat(appt_date[:10])
        view._calendar_month = view._calendar_selected_day.replace(day=1)
    except ValueError:
        pass
    refresh_calendar(view)


def delete_appointment(view) -> None:
    appt_id = getattr(view, "_selected_appointment_id", None)
    parent = _parent(view)
    if appt_id is None:
        messagebox.showinfo("Appointment", "Select an appointment first.", parent=parent)
        return
    if not messagebox.askyesno("Delete appointment", "Delete this appointment?", parent=parent):
        return
    view.app.db.delete_appointment(appt_id)
    clear_appointment_form(view)
    refresh_calendar(view)
