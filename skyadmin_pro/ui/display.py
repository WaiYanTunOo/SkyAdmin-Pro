"""Display scaling helpers for Windows high-DPI setups."""

from __future__ import annotations

import sys


def _windows_widget_scale(dpi: float) -> float:
    """Map system DPI to a modest CustomTkinter scale factor."""
    return max(1.0, min(1.35, dpi / 96.0))


def apply_high_dpi_scaling() -> float:
    """Apply per-monitor DPI awareness and modest CTk scaling on Windows.

    Returns the widget scaling factor applied (1.0 when unchanged).
    Must be called BEFORE first Tk() for DPI awareness to take effect;
    widget scaling is applied after Tk is ready.
    """
    if sys.platform != "win32":
        return 1.0

    # DPI awareness must be set before Tk init — try both v2 and fallback.
    # If Tk already exists, this is a no-op but harmless.
    try:
        import ctypes

        # Per-monitor v2 — avoids blurry Tk on 125%/150% displays.
        # Use SetProcessDpiAwarenessContext if available (Win10 1703+), else SetProcessDpiAwareness
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

    try:
        import ctypes

        import customtkinter as ctk

        # Prefer per-window DPI if a window exists, else system DPI
        dpi = 96.0
        try:
            # Try per-monitor via GetDpiForWindow if we can get a HWND
            hwnd = ctypes.windll.user32.GetActiveWindow()
            if hwnd:
                try:
                    dpi = float(ctypes.windll.user32.GetDpiForWindow(hwnd))
                except Exception:
                    dpi = float(ctypes.windll.user32.GetDpiForSystem())
            else:
                dpi = float(ctypes.windll.user32.GetDpiForSystem())
        except Exception:
            dpi = 96.0
        scale = _windows_widget_scale(dpi)
        if scale > 1.02:
            ctk.set_widget_scaling(scale)
            # Do NOT also set_window_scaling — it compounds (1.35*1.35=1.82)
            # Keep window scaling at 1.0 and let widget scaling handle it
            try:
                ctk.set_window_scaling(1.0)
            except Exception:
                pass
            return scale
    except Exception:
        pass
    return 1.0
