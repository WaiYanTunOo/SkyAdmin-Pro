"""Day appointment popup (add / edit / delete) for Dashboard Calendar."""

from __future__ import annotations

from datetime import date
from tkinter import TclError

import customtkinter as ctk

from skyadmin_pro.ui.theme import FONT_SIZE_XL

from .calendar_detail import build_day_list, refresh_day_list
from .calendar_form import build_calendar_form
from .calendar_form_state import clear_appointment_form, drop_form_refs, load_appointment_into_form

_POP_W, _POP_H = 440, 580


def open_day_popup(view, day: date, *, appt_id: int | str | None = None) -> None:
    close_day_popup(view)
    view._calendar_selected_day = day
    view._calendar_month = day.replace(day=1)
    root = view.winfo_toplevel()
    top = ctk.CTkToplevel(root)
    title = day.strftime("%A, %d %b %Y")
    top.title(title)
    top.transient(root)
    top.resizable(False, True)
    top.grid_columnconfigure(0, weight=1)
    top.grid_rowconfigure(1, weight=1)
    ctk.CTkLabel(
        top,
        text=title,
        font=ctk.CTkFont(size=FONT_SIZE_XL, weight="bold"),
        anchor="w",
    ).grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
    build_day_list(view, top)
    build_calendar_form(view, top)
    view._calendar_popup = top
    top.protocol("WM_DELETE_WINDOW", lambda: close_day_popup(view))
    top.bind("<Destroy>", lambda e: _on_destroy(view, e), add="+")
    top.bind("<Escape>", lambda _e: close_day_popup(view))
    if appt_id is not None:
        load_appointment_into_form(view, str(appt_id))
    else:
        clear_appointment_form(view)
    refresh_day_list(view)
    _place_and_show(top, root)


def close_day_popup(view) -> None:
    top = getattr(view, "_calendar_popup", None)
    view._calendar_popup = None
    drop_form_refs(view)
    if top is None:
        return
    try:
        top.grab_release()
    except (TclError, AttributeError):
        pass
    try:
        top.destroy()
    except (TclError, AttributeError):
        pass


def _place_and_show(top, root) -> None:
    try:
        top.update_idletasks()
        sw, sh = int(top.winfo_screenwidth()), int(top.winfo_screenheight())
        rx, ry = int(root.winfo_rootx()), int(root.winfo_rooty())
        rw = max(int(root.winfo_width()), 1)
        rh = max(int(root.winfo_height()), 1)
        x = rx + max(0, (rw - _POP_W) // 2)
        y = ry + max(0, (rh - _POP_H) // 2)
        x = max(8, min(x, sw - _POP_W - 8))
        y = max(8, min(y, sh - _POP_H - 8))
        top.geometry(f"{_POP_W}x{_POP_H}+{x}+{y}")
        top.lift()
        top.after_idle(lambda: _focus_popup(top))
    except (TclError, AttributeError):
        try:
            top.geometry(f"{_POP_W}x{_POP_H}")
        except (TclError, AttributeError):
            pass


def _focus_popup(top) -> None:
    try:
        if top.winfo_exists():
            top.focus_set()
    except (TclError, AttributeError):
        pass


def _on_destroy(view, event) -> None:
    if event.widget is not getattr(view, "_calendar_popup", None):
        return
    view._calendar_popup = None
    drop_form_refs(view)
