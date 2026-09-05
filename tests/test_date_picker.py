"""DatePickerField popup placement and open-popup tracking tests."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk
import tkinter as tk

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
        Path(__file__).resolve().parents[1] / "skyadmin_pro" / "ui" / "widgets.py"
    ).read_text(encoding="utf-8").split("class DatePickerField")[1].split("class FeedbackLabel")[0]
    assert "-topmost" not in class_src
    assert "grab_set" in class_src
    assert "transient" in class_src
    assert "_close_all_open()" in class_src
    assert "tk.TclError" in class_src
    assert "_grab_after_id" in class_src
    # U2: map via update/update_idletasks, not a fragile delayed grab retry.
    grab_src = class_src.split("def _grab_calendar")[1].split("def _open_calendar")[0]
    assert "after(" not in grab_src
    assert "update_idletasks()" in grab_src
    assert ".update()" in grab_src or "top.update()" in grab_src


def test_datepicker_rapid_multi_instance_switch_no_tcl_error():
    """Opening field B while A is open must not raise on destroyed focus/grab."""
    errors: list[BaseException] = []

    def _report(exc, val, tb):
        errors.append(val if isinstance(val, BaseException) else exc)

    root = ctk.CTk()
    root.withdraw()
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

        # Rapid switch: close-before-create must leave only f2 open.
        f2._open_calendar()
        root.update()
        root.update_idletasks()
        # Flush CTk titlebar after(10)/after(200) callbacks that used to
        # call focus_set on the destroyed first popup.
        root.after(250, root.quit)
        root.mainloop()

        assert f1._calendar_top is None
        assert f2._calendar_top is not None
        assert DatePickerField._widget_alive(f2._calendar_top)
        assert sum(1 for f in DatePickerField._open_fields) == 1
        assert f2 in DatePickerField._open_fields

        f2._close_calendar()
        root.update()
        assert not DatePickerField._open_fields
        assert not any(isinstance(err, tk.TclError) for err in errors), errors
    finally:
        root.report_callback_exception = prev
        DatePickerField._close_all_open()
        try:
            root.destroy()
        except tk.TclError:
            pass
