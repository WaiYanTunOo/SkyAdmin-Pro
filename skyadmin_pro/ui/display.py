"""Display scaling and responsive layout for 1080p / 4K / 8K."""

from __future__ import annotations

import sys
from dataclasses import dataclass

# Short-edge / width thresholds (physical pixels as reported by Tk).
_CLASS_8K = 7680
_CLASS_4K = 3840
_CLASS_QHD = 2560
_CLASS_FHD = 1920


@dataclass(frozen=True)
class LayoutMetrics:
    """Density tokens for a display class (logical layout, not DPI multiply)."""

    display_class: str  # "1080" | "1440" | "4k" | "8k"
    sidebar_width: int
    sidebar_collapsed: int
    form_sidebar_min: int
    form_sidebar_max: int
    content_pad: int
    card_pad: int
    min_width: int
    min_height: int
    suggested_zoom_percent: int


_METRICS: dict[str, LayoutMetrics] = {
    "1080": LayoutMetrics(
        display_class="1080",
        sidebar_width=260,
        sidebar_collapsed=56,
        form_sidebar_min=300,
        form_sidebar_max=420,
        content_pad=20,
        card_pad=14,
        min_width=1100,
        min_height=700,
        suggested_zoom_percent=100,
    ),
    "1440": LayoutMetrics(
        display_class="1440",
        sidebar_width=280,
        sidebar_collapsed=60,
        form_sidebar_min=340,
        form_sidebar_max=480,
        content_pad=24,
        card_pad=16,
        min_width=1200,
        min_height=760,
        suggested_zoom_percent=110,
    ),
    "4k": LayoutMetrics(
        display_class="4k",
        sidebar_width=300,
        sidebar_collapsed=64,
        form_sidebar_min=380,
        form_sidebar_max=560,
        content_pad=28,
        card_pad=18,
        min_width=1400,
        min_height=860,
        suggested_zoom_percent=125,
    ),
    "8k": LayoutMetrics(
        display_class="8k",
        sidebar_width=340,
        sidebar_collapsed=72,
        form_sidebar_min=440,
        form_sidebar_max=720,
        content_pad=36,
        card_pad=22,
        min_width=1600,
        min_height=960,
        suggested_zoom_percent=150,
    ),
}

_active: LayoutMetrics = _METRICS["1080"]


def classify_display(width: int, height: int) -> str:
    """Classify by the longer screen edge (covers landscape 1080 / 4K / 8K)."""
    edge = max(int(width or 0), int(height or 0))
    if edge >= _CLASS_8K:
        return "8k"
    if edge >= _CLASS_4K:
        return "4k"
    if edge >= _CLASS_QHD:
        return "1440"
    return "1080"


def metrics_for_screen(width: int, height: int) -> LayoutMetrics:
    return _METRICS[classify_display(width, height)]


def get_active_metrics() -> LayoutMetrics:
    return _active


def set_active_metrics(metrics: LayoutMetrics) -> LayoutMetrics:
    global _active
    _active = metrics
    return _active


def preferred_geometry(screen_w: int, screen_h: int) -> str:
    """Default window size: ~82% of the screen, clamped to class mins."""
    m = metrics_for_screen(screen_w, screen_h)
    w = max(m.min_width, min(max(1, screen_w - 80), int(screen_w * 0.82)))
    h = max(m.min_height, min(max(1, screen_h - 100), int(screen_h * 0.82)))
    return f"{w}x{h}"


def form_sidebar_width(content_width: int, metrics: LayoutMetrics | None = None) -> int:
    """Form sidebar minsize that grows with the content pane, within class clamps."""
    m = metrics or _active
    if content_width <= 0:
        return m.form_sidebar_min
    target = int(content_width * 0.24)
    return max(m.form_sidebar_min, min(m.form_sidebar_max, target))


def _windows_widget_scale(dpi: float) -> float:
    """Map system DPI to a modest CustomTkinter scale factor (diagnostic / optional)."""
    # Allow higher headroom for 200%+ (4K/8K) without exploding past 2.0.
    return max(1.0, min(2.0, dpi / 96.0))


def apply_high_dpi_scaling() -> float:
    """Apply per-monitor DPI awareness on Windows.

    Returns 1.0 — CustomTkinter reads system DPI after awareness is set.
    Do not call ``ctk.set_widget_scaling`` here (double-scales with OS DPI).
    """
    if sys.platform != "win32":
        return 1.0

    try:
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError, ImportError):
        pass

    return 1.0


def suggested_zoom_for_screen(width: int, height: int) -> str:
    """Zoom preset string when the user has not saved a preference."""
    pct = metrics_for_screen(width, height).suggested_zoom_percent
    return f"{pct}%"
