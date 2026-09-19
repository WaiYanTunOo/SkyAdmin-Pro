"""Hour/minute −/+ steppers with typed entry."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import FONT_SIZE_SM, FORM_LABEL_COLOR, FORM_LABEL_FONT_SIZE, TEXT_MUTED

from .calendar_time_logic import (
    clear_time_ui,
    commit_typed,
    get_stored_time,
    nudge_hour,
    nudge_minute,
    set_time_ui,
    split_time,
)

_NONE = "—"

__all__ = [
    "build_time_steppers",
    "clear_time_ui",
    "commit_typed",
    "get_stored_time",
    "nudge_hour",
    "nudge_minute",
    "set_time_ui",
    "split_time",
]


def build_time_steppers(view, parent):
    wrap = ctk.CTkFrame(parent, fg_color="transparent")
    wrap.grid_columnconfigure(0, weight=1)
    wrap.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(
        wrap, text="Time", anchor="w", font=ctk.CTkFont(size=FORM_LABEL_FONT_SIZE), text_color=FORM_LABEL_COLOR
    ).grid(row=0, column=0, columnspan=2, sticky="w")
    view._cal_hour = None
    view._cal_minute = 0
    view.cal_hour_var = ctk.StringVar(value=_NONE)
    view.cal_minute_var = ctk.StringVar(value=_NONE)
    view.cal_hour_entry = _unit(
        wrap,
        0,
        "Hour",
        view.cal_hour_var,
        lambda: nudge_hour(view, -1),
        lambda: nudge_hour(view, 1),
        lambda: commit_typed(view),
    )
    view.cal_minute_entry = _unit(
        wrap,
        1,
        "Minute",
        view.cal_minute_var,
        lambda: nudge_minute(view, -1),
        lambda: nudge_minute(view, 1),
        lambda: commit_typed(view),
    )
    ctk.CTkButton(
        wrap,
        text="Clear time",
        width=90,
        height=26,
        fg_color="transparent",
        border_width=1,
        font=ctk.CTkFont(size=FONT_SIZE_SM),
        text_color=TEXT_MUTED,
        command=lambda: clear_time_ui(view),
    ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
    return wrap


def _unit(parent, col, caption, var, on_minus, on_plus, on_commit):
    box = ctk.CTkFrame(parent, fg_color="transparent")
    box.grid(row=1, column=col, sticky="ew", padx=(0, 8) if col == 0 else (8, 0))
    ctk.CTkLabel(box, text=caption, text_color=TEXT_MUTED, font=ctk.CTkFont(size=FONT_SIZE_SM)).pack(anchor="w")
    row = ctk.CTkFrame(box, fg_color="transparent")
    row.pack(fill="x", pady=(2, 0))
    ctk.CTkButton(row, text="−", width=36, height=32, command=on_minus).pack(side="left")
    entry = ctk.CTkEntry(row, textvariable=var, width=48, height=32, justify="center")
    entry.pack(side="left", padx=6)
    entry.bind("<FocusOut>", lambda _e: on_commit())
    entry.bind("<Return>", lambda _e: on_commit())
    ctk.CTkButton(row, text="+", width=36, height=32, command=on_plus).pack(side="left")
    return entry
