"""Optional drag-and-drop support via tkinterdnd2."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tkinter import TclError
from typing import Any

import customtkinter as ctk

DND_FILES = None
DND_AVAILABLE = False
TkinterDnD = None

try:
    from tkinterdnd2 import DND_FILES as _DND_FILES
    from tkinterdnd2 import TkinterDnD as _TkinterDnD

    DND_FILES = _DND_FILES
    TkinterDnD = _TkinterDnD
    DND_AVAILABLE = True
except Exception:  # defensive: Tk teardown/callback
    pass


def dnd_base_class() -> type:
    if DND_AVAILABLE and TkinterDnD is not None:
        return type("CTkDnD", (ctk.CTk, TkinterDnD.DnDWrapper), {})
    return ctk.CTk


def init_dnd(window: Any) -> bool:
    if not DND_AVAILABLE or TkinterDnD is None:
        return False
    try:
        window.TkdndVersion = TkinterDnD._require(window)
        return True
    except Exception:
        return False


def parse_dropped_files(widget: Any, data: str) -> list[Path]:
    try:
        parts = widget.tk.splitlist(data)
    except (TclError, TypeError):
        parts = data.split()
    paths: list[Path] = []
    for raw in parts:
        text = str(raw).strip().strip("{}")
        if not text:
            continue
        path = Path(text)
        if path.exists():
            paths.append(path)
    return paths


def enable_drop(widget: Any, callback: Callable[[list[Path]], None], enabled: bool) -> None:
    if not enabled or not DND_AVAILABLE or DND_FILES is None:
        return
    try:
        widget.drop_target_register(DND_FILES)
        widget.dnd_bind(
            "<<Drop>>",
            lambda event: callback(parse_dropped_files(widget, event.data)),
        )
    except Exception:  # defensive: Tk teardown/callback
        pass
