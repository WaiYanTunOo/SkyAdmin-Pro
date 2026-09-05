"""DatePickerField popup placement tests."""

from __future__ import annotations

from skyadmin_pro.ui.widgets import calendar_popup_position


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
