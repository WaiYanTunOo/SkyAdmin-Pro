"""Message helpers for SkyAgent chat panel."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from typing import Any

from .bubbles import ChatBubble


def _winfo_ok(widget: Any) -> bool:
    """Return False if widget has been destroyed."""
    try:
        return widget.winfo_exists()
    except tk.TclError:
        return False


def safe_error_text(_err: str) -> str:
    """User-facing error bubble; never echo raw paths/SQL/URLs/keys."""
    return "Something went wrong. Try again."


def add_bubble(history: Any, text: str, *, is_user: bool) -> None:
    """Append a chat bubble to the history frame."""
    try:
        count = len(history.winfo_children())
    except tk.TclError:
        return
    bubble = ChatBubble(history, text=text, is_user=is_user, timestamp=datetime.now().strftime("%H:%M"))
    bubble.grid(row=count, column=0, sticky="ew", pady=4)
    scroll_to_bottom(history)


def scroll_to_bottom(history: Any) -> None:
    """Safely scroll the history frame to the bottom."""
    try:
        canvas = getattr(history, "_parent_canvas", None)
        if canvas is not None:
            canvas.yview_moveto(1.0)
    except (AttributeError, tk.TclError):
        pass


def trim_messages(messages: list[dict[str, str]], history: Any, max_msgs: int = 100) -> None:
    """Cap message count and destroy excess widgets."""
    while len(messages) > max_msgs:
        messages.pop(0)
    children = history.winfo_children()
    if len(children) > max_msgs + 1:
        for child in children[: len(children) - max_msgs - 1]:
            child.destroy()
        for i, child in enumerate(history.winfo_children()):
            child.grid(row=i, column=0, sticky="ew", pady=4)
