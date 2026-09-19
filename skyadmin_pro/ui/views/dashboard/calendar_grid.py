"""Paint the Dashboard Calendar month day grid."""

from __future__ import annotations

import calendar
from datetime import date

import customtkinter as ctk

from skyadmin_pro.ui.theme import FONT_SIZE_SM, TEXT_MUTED

from .calendar_day import build_day_cell

_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def redraw_month_grid(view) -> None:
    grid = getattr(view, "_calendar_grid", None)
    if grid is None:
        return
    _clear_day_cells(view, grid)
    month = getattr(view, "_calendar_month", date.today().replace(day=1))
    today = date.today()
    selected = getattr(view, "_calendar_selected_day", today)
    by_day = getattr(view, "_calendar_by_day", {}) or {}
    view.calendar_month_label.configure(text=f"{calendar.month_name[month.month]} {month.year}")
    _ensure_weekday_headers(view, grid)
    weeks = calendar.Calendar(firstweekday=calendar.MONDAY).monthdatescalendar(month.year, month.month)
    for row in range(1, 7):
        active = row <= len(weeks)
        grid.grid_rowconfigure(
            row, weight=1 if active else 0, uniform="calrow" if active else "", minsize=56 if active else 0
        )
    from .calendar_actions import on_appt_chip, on_day_click

    cells: dict[date, ctk.CTkFrame] = {}
    for r, week in enumerate(weeks):
        for c, day in enumerate(week):
            cell = build_day_cell(
                grid,
                day=day,
                in_month=day.month == month.month,
                is_today=day == today,
                is_selected=day == selected,
                appointments=by_day.get(day.isoformat(), []),
                on_day=lambda d: on_day_click(view, d),
                on_appt=lambda a: on_appt_chip(view, a),
            )
            cell._cal_in_month = day.month == month.month
            cell._cal_is_today = day == today
            for ch in cell.winfo_children():
                if isinstance(ch, ctk.CTkLabel):
                    cell._cal_num = ch
                    break
            cell.grid(row=r + 1, column=c, sticky="nsew", padx=2, pady=2)
            cells[day] = cell
    view._calendar_cells = cells


def _clear_day_cells(view, grid) -> None:
    cells = getattr(view, "_calendar_cells", None) or {}
    if cells:
        for cell in cells.values():
            try:
                cell.destroy()
            except Exception:
                pass
        view._calendar_cells = {}
        return
    for child in grid.winfo_children():
        child.destroy()
    view._calendar_headers_built = False


def _ensure_weekday_headers(view, grid) -> None:
    if getattr(view, "_calendar_headers_built", False):
        return
    for i, name in enumerate(_WEEKDAYS):
        ctk.CTkLabel(grid, text=name, text_color=TEXT_MUTED, font=ctk.CTkFont(size=FONT_SIZE_SM, weight="bold")).grid(
            row=0, column=i, sticky="ew", pady=(0, 4)
        )
    view._calendar_headers_built = True
