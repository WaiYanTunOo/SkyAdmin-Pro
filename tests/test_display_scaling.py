"""High-DPI scaling helper tests."""

from __future__ import annotations

import sys
from unittest.mock import patch

from skyadmin_pro.ui.display import _windows_widget_scale, apply_high_dpi_scaling


def test_windows_widget_scale_clamps_to_sane_range():
    assert _windows_widget_scale(96.0) == 1.0
    assert _windows_widget_scale(120.0) == 1.25
    assert _windows_widget_scale(144.0) == 1.35
    assert _windows_widget_scale(192.0) == 1.35


def test_apply_high_dpi_scaling_skips_non_windows():
    with patch.object(sys, "platform", "darwin"):
        assert apply_high_dpi_scaling() == 1.0


def test_apply_high_dpi_scaling_sets_ctk_on_windows():
    import ctypes

    with (
        patch.object(sys, "platform", "win32"),
        patch.object(ctypes.windll.shcore, "SetProcessDpiAwareness", return_value=0),
        patch.object(ctypes.windll.user32, "GetDpiForSystem", return_value=120),
        patch("customtkinter.set_widget_scaling") as set_widget,
        patch("customtkinter.set_window_scaling") as set_window,
    ):
        scale = apply_high_dpi_scaling()
        assert scale == 1.25
        set_widget.assert_called_once_with(1.25)
        set_window.assert_called_once_with(1.0)
