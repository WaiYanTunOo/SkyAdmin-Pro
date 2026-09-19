"""Appointment form fields inside the calendar day popup."""

from __future__ import annotations

from datetime import date

import customtkinter as ctk

from skyadmin_pro.ui.theme import FONT_SIZE_SM, FORM_ROW_GAP, TEXT_MUTED
from skyadmin_pro.ui.widgets import FormField

from .calendar_form_state import sync_date_label
from .calendar_time import build_time_steppers


def build_calendar_form(view, host) -> None:
    card = ctk.CTkFrame(host, fg_color="transparent")
    card.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
    card.grid_columnconfigure(0, weight=1)

    view.cal_title = ctk.StringVar()
    day = getattr(view, "_calendar_selected_day", None) or date.today()
    view.cal_date = ctk.StringVar(value=day.isoformat() if isinstance(day, date) else str(day)[:10])
    view.cal_location = ctk.StringVar()

    view.calendar_date_label = ctk.CTkLabel(
        card,
        text="",
        font=ctk.CTkFont(size=FONT_SIZE_SM),
        text_color=TEXT_MUTED,
        anchor="w",
    )
    view.calendar_date_label.grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 6))
    sync_date_label(view)

    pad = {"sticky": "ew", "padx": 4, "pady": (0, FORM_ROW_GAP)}
    FormField(card, label="Title", kind="entry", textvariable=view.cal_title).grid(row=1, column=0, **pad)
    build_time_steppers(view, card).grid(row=2, column=0, **pad)
    names = [""] + list(view.app.db.list_client_names())
    client_f = FormField(card, label="Client (optional)", kind="combo", values=names)
    client_f.grid(row=3, column=0, **pad)
    view.cal_client_field = client_f
    FormField(card, label="Location", kind="entry", textvariable=view.cal_location).grid(row=4, column=0, **pad)
    notes_f = FormField(card, label="Notes", kind="textbox", height=64)
    notes_f.grid(row=5, column=0, sticky="ew", padx=4, pady=(0, 8))
    view.cal_notes_field = notes_f
    _buttons(view, card)


def _buttons(view, card) -> None:
    btns = ctk.CTkFrame(card, fg_color="transparent")
    btns.grid(row=6, column=0, sticky="ew", padx=4, pady=(0, 4))
    from .calendar_form_state import clear_appointment_form
    from .calendar_mutate import delete_appointment, save_appointment
    from .calendar_popup import close_day_popup

    ctk.CTkButton(btns, text="New", width=70, command=lambda: clear_appointment_form(view)).pack(side="left")
    ctk.CTkButton(btns, text="Save", width=80, command=lambda: save_appointment(view)).pack(side="left", padx=(6, 0))
    ctk.CTkButton(
        btns,
        text="Delete",
        width=80,
        fg_color=("gray70", "gray35"),
        command=lambda: delete_appointment(view),
    ).pack(side="left", padx=(6, 0))
    ctk.CTkButton(
        btns,
        text="Close",
        width=80,
        fg_color="transparent",
        border_width=1,
        command=lambda: close_day_popup(view),
    ).pack(side="right")
