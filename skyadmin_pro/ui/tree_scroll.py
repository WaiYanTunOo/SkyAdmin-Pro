"""Scrollbar auto-hide helpers for ThemedTreeview."""

from __future__ import annotations

import tkinter as tk


def should_show_scroll(first: float, last: float, *, epsilon: float = 0.002) -> bool:
    """True when the viewable fraction is less than the full content."""
    try:
        return float(first) > epsilon or float(last) < 1.0 - epsilon
    except (TypeError, ValueError):
        return True


def apply_scrollbar_visibility(scrollbar, first: float, last: float, *, row: int, column: int, sticky: str) -> None:
    """Show or hide a gridded ttk scrollbar based on scroll fraction."""
    try:
        if should_show_scroll(first, last):
            scrollbar.set(first, last)
            if not scrollbar.winfo_ismapped():
                scrollbar.grid(row=row, column=column, sticky=sticky)
        else:
            scrollbar.set(0.0, 1.0)
            if scrollbar.winfo_ismapped():
                scrollbar.grid_remove()
    except tk.TclError:
        pass
