"""Multi-instance DatePickerField regression tests."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from skyadmin_pro.ui.widgets import DatePickerField


def test_two_instances_open_own_popups(tk_root) -> None:
    """Two DatePickerField instances can each open their own calendar popup."""
    f1 = DatePickerField(tk_root, var=ctk.StringVar(value="2026-09-01"))
    f2 = DatePickerField(tk_root, var=ctk.StringVar(value="2026-09-15"))
    f1.pack(padx=10, pady=10)
    f2.pack(padx=10, pady=10)
    tk_root.update()

    f1._open_calendar()
    tk_root.update()
    assert f1._calendar_top is not None
    assert DatePickerField._widget_alive(f1._calendar_top)
    assert f1 in DatePickerField._open_fields

    f2._open_calendar()
    tk_root.update()
    assert f2._calendar_top is not None
    assert DatePickerField._widget_alive(f2._calendar_top)
    assert f2 in DatePickerField._open_fields
    assert f1 in DatePickerField._open_fields
    assert len(DatePickerField._open_fields) == 2


def test_root_escape_closes_last_opened_popup(tk_root) -> None:
    """Root-level Escape closes only the most recently opened popup."""
    f1 = DatePickerField(tk_root, var=ctk.StringVar(value="2026-09-01"))
    f2 = DatePickerField(tk_root, var=ctk.StringVar(value="2026-09-15"))
    f1.pack(padx=10, pady=10)
    f2.pack(padx=10, pady=10)
    tk_root.update()

    f1._open_calendar()
    tk_root.update()
    assert f1._calendar_top is not None

    f2._open_calendar()
    tk_root.update()
    assert f2._calendar_top is not None
    assert f1._calendar_top is not None
    assert len(DatePickerField._open_fields) == 2

    DatePickerField._on_root_escape()
    tk_root.update()
    assert f2._calendar_top is None
    assert f1._calendar_top is not None
    assert len(DatePickerField._open_fields) == 1
    assert f1 in DatePickerField._open_fields

    DatePickerField._on_root_escape()
    tk_root.update()
    assert f1._calendar_top is None
    assert len(DatePickerField._open_fields) == 0


def test_click_outside_closes_correct_popup(tk_root) -> None:
    """Clicking outside a popup closes only that popup, leaving others open."""
    f1 = DatePickerField(tk_root, var=ctk.StringVar(value="2026-09-01"))
    f2 = DatePickerField(tk_root, var=ctk.StringVar(value="2026-09-15"))
    f1.pack(padx=10, pady=10)
    f2.pack(padx=10, pady=10)
    tk_root.update()

    f1._open_calendar()
    f2._open_calendar()
    tk_root.update()
    assert len(DatePickerField._open_fields) == 2

    event = tk.Event()
    event.x_root = -1
    event.y_root = -1
    DatePickerField._on_root_click(event)
    tk_root.update()
    assert len(DatePickerField._open_fields) == 0


def test_multiple_popups_dont_conflict_with_root_bindings(tk_root) -> None:
    """Multiple popups share root <Button-1> and <Escape> binds without conflict."""
    f1 = DatePickerField(tk_root, var=ctk.StringVar(value="2026-09-01"))
    f2 = DatePickerField(tk_root, var=ctk.StringVar(value="2026-09-15"))
    f1.pack(padx=10, pady=10)
    f2.pack(padx=10, pady=10)
    tk_root.update()

    f1._open_calendar()
    tk_root.update()
    root_id = id(tk_root)
    assert root_id in DatePickerField._root_click_binds
    assert root_id in DatePickerField._root_escape_binds

    f2._open_calendar()
    tk_root.update()
    assert root_id in DatePickerField._root_click_binds
    assert root_id in DatePickerField._root_escape_binds
    assert len(DatePickerField._open_fields) == 2


def test_root_escape_when_no_popup_closed_safely(tk_root) -> None:
    """Escape with no popups open should not raise errors."""
    f1 = DatePickerField(tk_root, var=ctk.StringVar(value="2026-09-01"))
    f1.pack(padx=10, pady=10)
    tk_root.update()
    DatePickerField._on_root_escape()
    tk_root.update()
    assert len(DatePickerField._open_fields) == 0


def test_close_all_open_clears_last_opened(tk_root) -> None:
    """_close_all_open should clear _last_opened."""
    f1 = DatePickerField(tk_root, var=ctk.StringVar(value="2026-09-01"))
    f2 = DatePickerField(tk_root, var=ctk.StringVar(value="2026-09-15"))
    f1.pack(padx=10, pady=10)
    f2.pack(padx=10, pady=10)
    tk_root.update()

    f1._open_calendar()
    tk_root.update()
    f2._open_calendar()
    tk_root.update()
    assert DatePickerField._last_opened is f2

    DatePickerField._close_all_open()
    tk_root.update()
    assert DatePickerField._last_opened is None
    assert len(DatePickerField._open_fields) == 0


def test_open_same_field_twice_replaces_popup(tk_root) -> None:
    """Opening the same field twice closes the old popup and opens a new one."""
    f1 = DatePickerField(tk_root, var=ctk.StringVar(value="2026-09-01"))
    f1.pack(padx=10, pady=10)
    tk_root.update()

    f1._open_calendar()
    tk_root.update()
    assert f1._calendar_top is not None
    assert len(DatePickerField._open_fields) == 1

    old_top = f1._calendar_top
    f1._open_calendar()
    tk_root.update()
    assert f1._calendar_top is not None
    assert f1._calendar_top is not old_top
    assert old_top is None or not DatePickerField._widget_alive(old_top)
    assert len(DatePickerField._open_fields) == 1
