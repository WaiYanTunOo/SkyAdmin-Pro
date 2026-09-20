"""DatePickerField popup placement and open-popup tracking tests."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from skyadmin_pro.ui.widgets import DatePickerField, calendar_popup_position


def test_calendar_popup_opens_below_field_by_default():
    x, y = calendar_popup_position(
        anchor_x=100,
        anchor_y=200,
        anchor_w=240,
        anchor_h=32,
        popup_w=360,
        popup_h=420,
        screen_w=1920,
        screen_h=1080,
    )
    assert x == 100
    assert y == 232


def test_calendar_popup_flips_above_near_screen_bottom():
    x, y = calendar_popup_position(
        anchor_x=100,
        anchor_y=900,
        anchor_w=240,
        anchor_h=32,
        popup_w=360,
        popup_h=420,
        screen_w=1920,
        screen_h=1080,
    )
    assert x == 100
    assert y == 480


def test_calendar_popup_shifts_left_when_off_screen_right():
    x, y = calendar_popup_position(
        anchor_x=1700,
        anchor_y=200,
        anchor_w=240,
        anchor_h=32,
        popup_w=360,
        popup_h=420,
        screen_w=1920,
        screen_h=1080,
    )
    assert x == 1552
    assert y == 232


def test_datepicker_class_tracks_open_fields():
    assert hasattr(DatePickerField, "_open_fields")
    assert hasattr(DatePickerField, "_root_click_binds")
    assert hasattr(DatePickerField, "_ensure_root_binds")
    assert hasattr(DatePickerField, "_close_all_open")
    assert hasattr(DatePickerField, "_widget_alive")
    class_src = (
        (Path(__file__).resolve().parents[1] / "skyadmin_pro" / "ui" / "widgets.py")
        .read_text(encoding="utf-8")
        .split("class DatePickerField")[1]
        .split("class FeedbackLabel")[0]
    )
    assert "-topmost" not in class_src
    assert "grab_set" in class_src
    assert "transient" in class_src
    assert "_close_calendar()" in class_src
    assert "tk.TclError" in class_src
    assert "_last_opened" in class_src
    # U2: map via update/update_idletasks, not a fragile delayed grab retry.
    grab_src = class_src.split("def _grab_calendar")[1].split("def _open_calendar")[0]
    assert "after(" not in grab_src
    assert "update_idletasks()" in grab_src
    assert ".update()" in grab_src or "top.update()" in grab_src


def test_datepicker_rapid_multi_instance_switch_no_tcl_error(tk_root) -> None:
    """Opening field B while A is open must not raise on destroyed focus/grab."""
    errors: list[BaseException] = []
    root = tk_root

    def _report(exc, val, tb):
        errors.append(val if isinstance(val, BaseException) else exc)

    prev = root.report_callback_exception
    root.report_callback_exception = _report
    try:
        f1 = DatePickerField(root, var=ctk.StringVar(value="2026-09-01"))
        f1.pack()
        f2 = DatePickerField(root, var=ctk.StringVar(value="2026-09-15"))
        f2.pack()
        root.update()

        f1._open_calendar()
        root.update()
        assert f1._calendar_top is not None
        assert DatePickerField._widget_alive(f1._calendar_top)

        # Field B opens its own popup; field A's popup stays open.
        f2._open_calendar()
        root.update()
        root.update_idletasks()
        assert f1._calendar_top is not None
        assert f2._calendar_top is not None
        assert DatePickerField._widget_alive(f2._calendar_top)
        assert len(DatePickerField._open_fields) == 2
        assert f1 in DatePickerField._open_fields
        assert f2 in DatePickerField._open_fields

        f1._close_calendar()
        root.update()
        assert f1._calendar_top is None
        assert f2._calendar_top is not None
        assert len(DatePickerField._open_fields) == 1

        f2._close_calendar()
        root.update()
        assert not DatePickerField._open_fields
        assert not any(isinstance(err, tk.TclError) for err in errors), errors
    finally:
        root.report_callback_exception = prev


def _month_label(top: ctk.CTkToplevel) -> str:
    """Return the current month_label text from an open calendar popup."""
    body = top.winfo_children()[0]
    nav = body.winfo_children()[0]
    for child in nav.winfo_children():
        if isinstance(child, ctk.CTkLabel):
            return child.cget("text")
    raise AssertionError("month label not found in calendar nav")


def _month_arrows(top: ctk.CTkToplevel) -> tuple[tk.Widget, tk.Widget]:
    """Return (prev_arrow, next_arrow) CTkButtons from the month nav row."""
    body = top.winfo_children()[0]
    nav = body.winfo_children()[0]
    right_nav = nav.winfo_children()[-1]
    buttons = [w for w in right_nav.winfo_children() if isinstance(w, ctk.CTkButton)]
    return buttons[0], buttons[1]


def test_calendar_month_arrow_advances_month(tk_root) -> None:
    """Clicking the month-right arrow advances the displayed month."""
    field = DatePickerField(tk_root, var=ctk.StringVar(value="2026-09-15"))
    field.pack()
    tk_root.update()

    field._open_calendar()
    tk_root.update()
    top = field._calendar_top
    assert top is not None

    label = _month_label(top)
    assert "September" in label
    assert "2026" in label

    _prev, nxt = _month_arrows(top)
    nxt.invoke()
    tk_root.update()

    label = _month_label(top)
    assert "October" in label
    assert "2026" in label

    field._close_calendar()
    tk_root.update()


def test_calendar_month_arrow_wraps_year(tk_root) -> None:
    """Clicking month-right from December rolls into January of the next year."""
    field = DatePickerField(tk_root, var=ctk.StringVar(value="2026-12-10"))
    field.pack()
    tk_root.update()

    field._open_calendar()
    tk_root.update()
    top = field._calendar_top
    assert top is not None

    label = _month_label(top)
    assert "December" in label

    _prev, nxt = _month_arrows(top)
    nxt.invoke()
    tk_root.update()

    label = _month_label(top)
    assert "January" in label
    assert "2027" in label

    field._close_calendar()
    tk_root.update()


def test_calendar_month_menu_select(tk_root) -> None:
    """Selecting a month from the dropdown updates the calendar grid."""
    field = DatePickerField(tk_root, var=ctk.StringVar(value="2026-06-01"))
    field.pack()
    tk_root.update()

    field._open_calendar()
    tk_root.update()
    top = field._calendar_top
    assert top is not None

    body = top.winfo_children()[0]
    nav = body.winfo_children()[0]
    right_nav = nav.winfo_children()[-1]
    month_menu = [w for w in right_nav.winfo_children() if isinstance(w, ctk.CTkOptionMenu)][0]
    cmd = month_menu.cget("command")
    cmd("March")
    tk_root.update()

    label = _month_label(top)
    assert "March" in label
    assert "2026" in label

    field._close_calendar()
    tk_root.update()


def test_calendar_grid_renders_all_weeks(tk_root) -> None:
    """After month change the day grid contains the correct number of day buttons."""
    field = DatePickerField(tk_root, var=ctk.StringVar(value="2026-02-01"))
    field.pack()
    tk_root.update()

    field._open_calendar()
    tk_root.update()
    top = field._calendar_top
    assert top is not None

    body = top.winfo_children()[0]
    grid_frame = body.winfo_children()[1]
    day_buttons = [w for w in grid_frame.winfo_children() if isinstance(w, ctk.CTkButton)]
    # Feb 2026 has 28 days
    assert len(day_buttons) == 28

    # Navigate to March (31 days)
    _prev, nxt = _month_arrows(top)
    nxt.invoke()
    tk_root.update()

    day_buttons = [w for w in grid_frame.winfo_children() if isinstance(w, ctk.CTkButton)]
    assert len(day_buttons) == 31

    label = _month_label(top)
    assert "March" in label

    field._close_calendar()
    tk_root.update()
