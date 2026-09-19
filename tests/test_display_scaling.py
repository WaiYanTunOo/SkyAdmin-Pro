"""High-DPI and multi-resolution layout helper tests."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from skyadmin_pro.ui.display import (
    _windows_widget_scale,
    apply_high_dpi_scaling,
    classify_display,
    form_sidebar_width,
    metrics_for_screen,
    preferred_geometry,
    suggested_zoom_for_screen,
)


def test_windows_widget_scale_clamps_to_sane_range():
    assert _windows_widget_scale(96.0) == 1.0
    assert _windows_widget_scale(120.0) == 1.25
    assert _windows_widget_scale(144.0) == 1.5
    assert _windows_widget_scale(192.0) == 2.0
    assert _windows_widget_scale(288.0) == 2.0


def test_classify_display_1080_4k_8k():
    assert classify_display(1920, 1080) == "1080"
    assert classify_display(2560, 1440) == "1440"
    assert classify_display(3840, 2160) == "4k"
    assert classify_display(7680, 4320) == "8k"
    assert classify_display(1080, 1920) == "1080"  # portrait FHD


def test_metrics_scale_up_with_class():
    m1080 = metrics_for_screen(1920, 1080)
    m4k = metrics_for_screen(3840, 2160)
    m8k = metrics_for_screen(7680, 4320)
    assert m1080.sidebar_width < m4k.sidebar_width < m8k.sidebar_width
    assert m1080.form_sidebar_min < m4k.form_sidebar_min < m8k.form_sidebar_min
    assert m1080.suggested_zoom_percent <= m4k.suggested_zoom_percent <= m8k.suggested_zoom_percent


def test_preferred_geometry_uses_most_of_screen():
    geo = preferred_geometry(3840, 2160)
    w, h = geo.split("x")
    assert int(w) >= 1400
    assert int(h) >= 860
    assert int(w) <= 3840
    assert int(h) <= 2160


def test_form_sidebar_width_clamped():
    m = metrics_for_screen(1920, 1080)
    assert form_sidebar_width(800, m) == m.form_sidebar_min
    assert form_sidebar_width(5000, m) == m.form_sidebar_max
    mid = form_sidebar_width(2000, m)
    assert m.form_sidebar_min <= mid <= m.form_sidebar_max


def test_suggested_zoom_strings():
    assert suggested_zoom_for_screen(1920, 1080) == "100%"
    assert suggested_zoom_for_screen(3840, 2160) == "125%"
    assert suggested_zoom_for_screen(7680, 4320) == "150%"


def test_apply_high_dpi_scaling_skips_non_windows():
    with patch.object(sys, "platform", "darwin"):
        assert apply_high_dpi_scaling() == 1.0


@pytest.mark.skipif(sys.platform != "win32", reason="requires Windows ctypes")
def test_apply_high_dpi_scaling_sets_ctk_on_windows():
    import ctypes

    with (
        patch.object(sys, "platform", "win32"),
        patch.object(ctypes.windll.shcore, "SetProcessDpiAwareness", return_value=0),
    ):
        scale = apply_high_dpi_scaling()
        assert scale == 1.0
