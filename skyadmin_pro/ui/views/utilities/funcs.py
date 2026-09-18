from __future__ import annotations

import tkinter.font as _tkfont

import customtkinter as ctk

from ._const_1 import _EDITOR_FONT_CANDIDATES
from ._const_2 import _EDITOR_FONT_FAMILY


def _editor_font(size: int = 13) -> ctk.CTkFont:
    global _EDITOR_FONT_FAMILY
    if _EDITOR_FONT_FAMILY is None:
        try:
            available = set(_tkfont.families())
        except Exception:
            available = set()
        _EDITOR_FONT_FAMILY = next(
            (name for name in _EDITOR_FONT_CANDIDATES if name in available),
            "TkDefaultFont",
        )
    return ctk.CTkFont(family=_EDITOR_FONT_FAMILY, size=size)
