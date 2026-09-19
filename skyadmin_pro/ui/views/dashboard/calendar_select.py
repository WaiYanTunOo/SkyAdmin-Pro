"""Cheap calendar day-selection highlight (no full grid rebuild)."""

from __future__ import annotations

from datetime import date

import customtkinter as ctk

from skyadmin_pro.ui.theme import ACCENT, CONTENT_BG, FONT_SIZE_SM, TEXT_FAINT, TEXT_INVERSE

_SEL_BG = ("#dbeafe", "#1e3a5f")
_TODAY_BG = ("#eff6ff", "#172554")
_IN_BG = ("#f8fafc", "#333333")
_OUT_BG = ("#f1f5f9", "#1f1f1f")


def paint_selection(view, previous: date | None = None) -> None:
    """Update selection highlight without destroying the month grid."""
    cells = getattr(view, "_calendar_cells", None) or {}
    if not cells:
        from .calendar_grid import redraw_month_grid

        redraw_month_grid(view)
        return
    selected = getattr(view, "_calendar_selected_day", None)
    for day in {previous, selected}:
        if day is None:
            continue
        cell = cells.get(day)
        if cell is None:
            continue
        try:
            if not cell.winfo_exists():
                continue
        except Exception:
            continue
        style_cell(cell, is_selected=(day == selected))


def style_cell(cell, *, is_selected: bool) -> None:
    in_month = bool(getattr(cell, "_cal_in_month", True))
    is_today = bool(getattr(cell, "_cal_is_today", False))
    if is_selected:
        fg, border, bw = _SEL_BG, ACCENT, 3
    elif is_today:
        fg, border, bw = _TODAY_BG, ACCENT, 2
    elif in_month:
        fg, border, bw = _IN_BG, CONTENT_BG, 1
    else:
        fg, border, bw = _OUT_BG, CONTENT_BG, 1
    cell.configure(fg_color=fg, border_width=bw, border_color=border)
    lbl = getattr(cell, "_cal_num", None)
    if lbl is None:
        return
    color = ACCENT if (is_today or is_selected) else (TEXT_INVERSE if in_month else TEXT_FAINT)
    weight = "bold" if (is_today or is_selected or in_month) else "normal"
    try:
        lbl.configure(text_color=color, font=ctk.CTkFont(size=FONT_SIZE_SM, weight=weight))
    except Exception:
        pass
