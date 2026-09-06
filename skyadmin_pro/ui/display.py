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
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:  # defensive: Tk teardown/callback
        pass

    # CustomTkinter automatically reads system DPI after awareness is set.
    # Do NOT manually call ctk.set_widget_scaling(scale) here, as it results
    # in multiplicative double-scaling (huge fonts).
    return 1.0
