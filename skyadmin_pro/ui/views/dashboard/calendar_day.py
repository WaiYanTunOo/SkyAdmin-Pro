"""One day cell in the Dashboard month calendar grid."""

from __future__ import annotations

from datetime import date

import customtkinter as ctk

from skyadmin_pro.ui.theme import (
    ACCENT,
    CARD_BG,
    CONTENT_BG,
    FONT_SIZE_SM,
    SIDEBAR_HOVER_BG,
    TEXT_FAINT,
    TEXT_INVERSE,
    TEXT_MUTED,
)

_MAX_CHIPS = 2
_OUT_BG = ("#f1f5f9", "#1f1f1f")
_IN_BG = ("#f8fafc", "#333333")
_SEL_BG = ("#dbeafe", "#1e3a5f")
_TODAY_BG = ("#eff6ff", "#172554")


def build_day_cell(
    parent,
    *,
    day: date,
    in_month: bool,
    is_today: bool,
    is_selected: bool,
    appointments: list,
    on_day,
    on_appt,
) -> ctk.CTkFrame:
    if is_selected:
        fg, border, bw = _SEL_BG, ACCENT, 3
    elif is_today:
        fg, border, bw = _TODAY_BG, ACCENT, 2
    elif in_month:
        fg, border, bw = _IN_BG, CONTENT_BG, 1
    else:
        fg, border, bw = _OUT_BG, CONTENT_BG, 1
    cell = ctk.CTkFrame(parent, corner_radius=8, fg_color=fg, border_width=bw, border_color=border)
    cell.grid_columnconfigure(0, weight=1)
    cell.grid_rowconfigure(1, weight=1)
    num_color = ACCENT if (is_today or is_selected) else (TEXT_INVERSE if in_month else TEXT_FAINT)
    weight = "bold" if (is_today or is_selected or in_month) else "normal"
    lbl = ctk.CTkLabel(
        cell,
        text=str(day.day),
        font=ctk.CTkFont(size=FONT_SIZE_SM, weight=weight),
        text_color=num_color,
        anchor="ne",
    )
    lbl.grid(row=0, column=0, sticky="ne", padx=6, pady=(4, 0))

    def open_day(_e=None, d=day):
        on_day(d)

    lbl.bind("<Button-1>", open_day)
    cell.bind("<Button-1>", open_day)
    _chips(cell, appointments, in_month, on_day, on_appt, day)
    return cell


def _chips(cell, appointments: list, in_month: bool, on_day, on_appt, day: date) -> None:
    host = ctk.CTkFrame(cell, fg_color="transparent")
    host.grid(row=1, column=0, sticky="nsew", padx=3, pady=(0, 3))
    host.bind("<Button-1>", lambda _e, d=day: on_day(d))
    for appt in appointments[:_MAX_CHIPS]:
        title = (appt.get("title") or "")[:14]
        t = (appt.get("appt_time") or "").strip()
        text = f"{t} {title}".strip() if t else (title or "•")
        btn = ctk.CTkButton(
            host,
            text=text,
            height=20,
            font=ctk.CTkFont(size=10),
            fg_color=SIDEBAR_HOVER_BG if in_month else CARD_BG,
            text_color=TEXT_INVERSE if in_month else TEXT_FAINT,
            hover_color=("gray70", "gray30"),
            corner_radius=4,
            command=lambda a=appt: on_appt(a),
        )
        btn.pack(fill="x", pady=1)
    extra = len(appointments) - _MAX_CHIPS
    if extra > 0:
        more = ctk.CTkLabel(host, text=f"+{extra} more", font=ctk.CTkFont(size=10), text_color=TEXT_MUTED, anchor="w")
        more.pack(fill="x")
        more.bind("<Button-1>", lambda _e, d=day: on_day(d))
