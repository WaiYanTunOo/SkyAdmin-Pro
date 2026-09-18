import ctypes
from pathlib import Path

import customtkinter as ctk

FONT_FAMILY = "Noto Sans"
FONT_FAMILY_FALLBACK = "Segoe UI"
FR_PRIVATE = 0x10


def load_fonts() -> None:
    font_dir = Path(__file__).parent.parent / "assets" / "fonts"
    if not font_dir.exists():
        return

    try:
        gdi32 = ctypes.WinDLL("gdi32")
    except Exception:
        return

    for font_file in font_dir.glob("*.ttf"):
        path = str(font_file.resolve())
        gdi32.AddFontResourceExW(path, FR_PRIVATE, 0)
        if hasattr(ctk.FontManager, "load_font"):
            ctk.FontManager.load_font(path)
