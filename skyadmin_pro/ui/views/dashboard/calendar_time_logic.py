"""Hour/minute stepper logic (nudge, type, clear)."""

from __future__ import annotations

from tkinter import TclError

_NONE = "—"


def nudge_hour(view, delta: int) -> None:
    commit_typed(view)
    h = getattr(view, "_cal_hour", None)
    if h is None:
        view._cal_hour = 9 if delta > 0 else 8
        view._cal_minute = int(getattr(view, "_cal_minute", 0) or 0)
    else:
        view._cal_hour = (int(h) + delta) % 24
    _paint(view)


def nudge_minute(view, delta: int) -> None:
    commit_typed(view)
    h = getattr(view, "_cal_hour", None)
    if h is None:
        view._cal_hour = 9
        view._cal_minute = 0 if delta < 0 else 1
    else:
        view._cal_minute = (int(getattr(view, "_cal_minute", 0)) + delta) % 60
    _paint(view)


def clear_time_ui(view) -> None:
    view._cal_hour = None
    view._cal_minute = 0
    _paint(view)


def set_time_ui(view, raw: str | None) -> None:
    h, m = split_time(raw)
    view._cal_hour = h
    view._cal_minute = m if h is not None else 0
    _paint(view)


def get_stored_time(view) -> str | None:
    if getattr(view, "cal_hour_var", None) is not None:
        commit_typed(view)
    h = getattr(view, "_cal_hour", None)
    if h is None:
        return None
    m = int(getattr(view, "_cal_minute", 0) or 0)
    return f"{int(h):02d}:{m:02d}"


def commit_typed(view) -> None:
    """Parse entry text into _cal_hour / _cal_minute; invalid → keep prior and repaint."""
    if getattr(view, "cal_hour_var", None) is None:
        return
    h_raw = _var_text(view, "cal_hour_var")
    m_raw = _var_text(view, "cal_minute_var")
    if h_raw in ("", _NONE):
        view._cal_hour = None
        view._cal_minute = 0
        _paint(view)
        return
    h = _parse_int(h_raw, 0, 23)
    m = _parse_int(m_raw if m_raw not in ("", _NONE) else "0", 0, 59)
    if h is None or m is None:
        _paint(view)
        return
    view._cal_hour = h
    view._cal_minute = m
    _paint(view)


def split_time(raw: str | None) -> tuple[int | None, int]:
    s = (raw or "").strip()
    if not s:
        return None, 0
    try:
        h_s, m_s = s.split(":", 1)
        h, m = int(h_s), int(m_s)
    except (ValueError, IndexError):
        return None, 0
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None, 0
    return h, m


def _var_text(view, name: str) -> str:
    var = getattr(view, name, None)
    if var is None:
        return ""
    try:
        return str(var.get()).strip()
    except (TclError, AttributeError):
        return ""


def _parse_int(raw: str, lo: int, hi: int) -> int | None:
    try:
        n = int(raw)
    except ValueError:
        return None
    return n if lo <= n <= hi else None


def _paint(view) -> None:
    h = getattr(view, "_cal_hour", None)
    m = int(getattr(view, "_cal_minute", 0) or 0)
    hour_t = _NONE if h is None else f"{int(h):02d}"
    min_t = _NONE if h is None else f"{m:02d}"
    for name, text in (("cal_hour_var", hour_t), ("cal_minute_var", min_t)):
        var = getattr(view, name, None)
        if var is None:
            continue
        try:
            if str(var.get()) != text:
                var.set(text)
        except (TclError, AttributeError):
            pass
