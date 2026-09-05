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
    ):
        scale = apply_high_dpi_scaling()
        assert scale == 1.0
