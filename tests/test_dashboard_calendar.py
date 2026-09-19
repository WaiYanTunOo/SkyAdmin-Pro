"""Dashboard Calendar tab uses a full-width month grid + day popup."""

from datetime import date
from pathlib import Path

from skyadmin_pro.ui.views.dashboard.calendar_actions import _visible_range
from skyadmin_pro.ui.views.dashboard.calendar_month import step_month
from skyadmin_pro.ui.views.dashboard.calendar_time import get_stored_time, split_time


def _src(*parts: str) -> str:
    return (Path(__file__).resolve().parents[1].joinpath(*parts)).read_text(encoding="utf-8")


def test_calendar_tab_is_month_grid_not_tree():
    tab = _src("skyadmin_pro", "ui", "views", "dashboard", "calendar_tab.py")
    day = _src("skyadmin_pro", "ui", "views", "dashboard", "calendar_day.py")
    grid = _src("skyadmin_pro", "ui", "views", "dashboard", "calendar_grid.py")
    form = _src("skyadmin_pro", "ui", "views", "dashboard", "calendar_form.py")
    popup = _src("skyadmin_pro", "ui", "views", "dashboard", "calendar_popup.py")
    actions = _src("skyadmin_pro", "ui", "views", "dashboard", "calendar_actions.py")
    assert "ThemedTreeview" not in tab
    assert "calendar_tree" not in tab
    assert "build_month_panel" in tab
    assert "build_day_panel" not in tab
    assert "build_calendar_form" not in tab
    assert "build_day_cell" in day
    assert "monthdatescalendar" in grid
    assert "Mon" in grid and "Sun" in grid
    assert 'kind="date"' not in form
    assert "calendar_date_label" in form
    assert "build_time_steppers" in form
    assert "cal_location" in form
    assert "CTkToplevel" in popup
    assert "open_day_popup" in popup
    assert "make_modal" not in popup
    assert "grab_set" not in popup
    assert "open_day_popup" in actions
    assert "Close" in form


def test_calendar_step_month_and_visible_range():
    assert step_month(date(2026, 1, 1), -1) == date(2025, 12, 1)
    assert step_month(date(2026, 12, 1), 1) == date(2027, 1, 1)
    start, end = _visible_range(date(2026, 9, 1))
    assert start <= "2026-09-01" <= end
    assert start.startswith("2026-08") or start.startswith("2026-09")
    assert end.startswith("2026-09") or end.startswith("2026-10")


def test_calendar_toolbar_hosts_upcoming_count():
    month = _src("skyadmin_pro", "ui", "views", "dashboard", "calendar_month.py")
    tab = _src("skyadmin_pro", "ui", "views", "dashboard", "calendar_tab.py")
    assert "calendar_count_label" in month
    assert "calendar_count_label" not in tab
    assert 'text="Calendar"' not in tab


def test_calendar_popup_has_escape_and_no_datepicker():
    popup = _src("skyadmin_pro", "ui", "views", "dashboard", "calendar_popup.py")
    form = _src("skyadmin_pro", "ui", "views", "dashboard", "calendar_form.py")
    assert 'bind("<Escape>"' in popup
    assert "make_modal" not in popup
    assert "grab_set" not in popup
    assert "grab_release" in popup
    assert "_place_and_show" in popup
    assert "focus_force" not in popup
    assert "-topmost" not in popup
    assert "DatePickerField" not in form
    assert 'kind="date"' not in form
    assert "New" in form and "Save" in form and "Delete" in form and "Close" in form


def test_calendar_time_norm_and_day_chip_targets():
    assert split_time("") == (None, 0)
    assert split_time("9:7") == (9, 7)
    assert split_time("23:59") == (23, 59)
    time_src = _src("skyadmin_pro", "ui", "views", "dashboard", "calendar_time.py")
    assert "nudge_hour" in time_src and "nudge_minute" in time_src
    assert "build_time_steppers" in time_src
    assert "CTkEntry" in time_src and "commit_typed" in time_src
    assert "CTkOptionMenu" not in time_src and 'kind="option"' not in time_src
    assert "get_stored_time" in time_src
    day = _src("skyadmin_pro", "ui", "views", "dashboard", "calendar_day.py")
    assert "on_day(d)" in day
    assert "+{extra} more" in day
    state = _src("skyadmin_pro", "ui", "views", "dashboard", "calendar_form_state.py")
    assert "popup_form_ready" in state and "clear_time_ui" in state
    form = _src("skyadmin_pro", "ui", "views", "dashboard", "calendar_form.py")
    assert "build_time_steppers" in form

    # Runtime: unset → None; after set via split
    class _V:
        pass

    v = _V()
    v._cal_hour = None
    v._cal_minute = 0
    assert get_stored_time(v) is None
    v._cal_hour, v._cal_minute = 9, 5
    assert get_stored_time(v) == "09:05"
