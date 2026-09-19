"""Day appointment list inside the calendar day popup."""

from __future__ import annotations

from datetime import date
from tkinter import TclError

import customtkinter as ctk

from skyadmin_pro.ui.theme import FONT_SIZE_SM, SIDEBAR_HOVER_BG, TEXT_INVERSE, TEXT_MUTED, TEXT_SUBTLE


def build_day_list(view, parent) -> None:
    wrap = ctk.CTkFrame(parent, fg_color="transparent")
    wrap.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 4))
    wrap.grid_columnconfigure(0, weight=1)
    wrap.grid_rowconfigure(1, weight=1)
    ctk.CTkLabel(
        wrap,
        text="Appointments",
        text_color=TEXT_SUBTLE,
        font=ctk.CTkFont(size=FONT_SIZE_SM),
        anchor="w",
    ).grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 2))
    view._calendar_day_list = ctk.CTkScrollableFrame(wrap, fg_color="transparent", height=120)
    view._calendar_day_list.grid(row=1, column=0, sticky="nsew")
    view._calendar_day_list.grid_columnconfigure(0, weight=1)


def refresh_day_list(view) -> None:
    host = getattr(view, "_calendar_day_list", None)
    if host is None:
        return
    try:
        if not host.winfo_exists():
            return
        for child in list(host.winfo_children()):
            child.destroy()
    except (TclError, AttributeError):
        return
    day = getattr(view, "_calendar_selected_day", date.today())
    rows = (getattr(view, "_calendar_by_day", {}) or {}).get(
        day.isoformat() if isinstance(day, date) else str(day)[:10], []
    )
    if not rows:
        ctk.CTkLabel(host, text="None for this day", text_color=TEXT_MUTED, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=4, pady=6
        )
        return
    from .calendar_form_state import load_appointment_into_form

    for i, appt in enumerate(rows):
        t = (appt.get("appt_time") or "").strip()
        title = appt.get("title") or "Appointment"
        text = f"{t}  {title}".strip() if t else title
        ctk.CTkButton(
            host,
            text=text,
            anchor="w",
            height=30,
            fg_color=SIDEBAR_HOVER_BG,
            text_color=TEXT_INVERSE,
            hover_color=("gray70", "gray30"),
            command=lambda a=appt: load_appointment_into_form(view, str(a.get("id"))),
        ).grid(row=i, column=0, sticky="ew", pady=2, padx=2)
