"""Row-height policy for ThemedTreeview.set_rows (D7 helper)."""

from __future__ import annotations

_FILL_CAP = 60  # raised ceiling when viewport size is not yet known
_EMBED_CAP = 20  # legacy cap for compact / non-fill trees


def fills_vertically(widget) -> bool:
    try:
        sticky = str(widget.grid_info().get("sticky") or "")
        return "n" in sticky and "s" in sticky
    except Exception:
        return False


def rows_height(widget, *, row_count: int, empty: bool, showheight: int, visible_rows: int) -> int:
    """Empty fill panels keep showheight; embed empty stays 1; fill grows with viewport."""
    floor = max(1, int(showheight))
    if empty:
        return floor if fills_vertically(widget) else 1
    n = max(1, int(row_count))
    if not fills_vertically(widget):
        return min(_EMBED_CAP, max(1, n))
    avail = max(0, int(visible_rows))
    if avail > floor:
        return max(floor, min(n, avail))
    return max(floor, min(n, _FILL_CAP))
