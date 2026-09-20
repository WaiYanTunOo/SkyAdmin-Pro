"""Theme cache tests — verify apply_form_theme() skips already-themed widgets."""

from __future__ import annotations

import customtkinter as ctk
import pytest

from skyadmin_pro.ui.widgets import _THEMED_WIDGET_CACHE, apply_form_theme, should_apply_theme


@pytest.fixture(scope="module")
def app_root():
    """Provide a single CTk root window for all widget tests in this module."""
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    yield root
    try:
        root.destroy()
    except Exception:
        pass
    ctk.set_appearance_mode("dark")
    should_apply_theme()


def test_apply_form_theme_skips_already_themed_on_second_call(app_root, monkeypatch):
    """Second call with unchanged mode should skip redundant walks."""
    root = app_root

    ctk.set_appearance_mode("dark")
    _THEMED_WIDGET_CACHE.clear()
    should_apply_theme()

    # First call: widgets get themed and cached
    apply_form_theme(root)
    assert getattr(root, "_subtree_themed_mode", None) == "Dark"

    # Mock winfo_children to detect if a second walk would occur
    children_seen: list = []
    original_winfo_children = root.winfo_children

    def counting_children():
        children_seen.append("walk")
        return original_winfo_children()

    monkeypatch.setattr(root, "winfo_children", counting_children)

    # Second call: subtree is already themed for "Dark", should return early
    apply_form_theme(root)
    assert children_seen == []


def test_apply_form_theme_re_themes_when_mode_changes(app_root, monkeypatch):
    """Changing mode should re-theme and walk the tree again."""
    root = app_root

    ctk.set_appearance_mode("dark")
    _THEMED_WIDGET_CACHE.clear()
    should_apply_theme()

    apply_form_theme(root)
    assert getattr(root, "_subtree_themed_mode", None) == "Dark"

    # Switch mode and clear cache
    should_apply_theme()
    ctk.set_appearance_mode("light")
    should_apply_theme()

    children_seen: list = []
    original_winfo_children = root.winfo_children

    def counting_children():
        children_seen.append("walk")
        return original_winfo_children()

    monkeypatch.setattr(root, "winfo_children", counting_children)

    apply_form_theme(root)
    assert len(children_seen) > 0


def test_apply_form_theme_caches_by_theme_name(app_root):
    """Cache is keyed by theme name, so different modes don't collide."""
    ctk.set_appearance_mode("dark")
    _THEMED_WIDGET_CACHE.clear()
    should_apply_theme()

    widget = ctk.CTkEntry(app_root)
    apply_form_theme(widget)

    # Widget should be cached under "Dark"
    assert id(widget) in _THEMED_WIDGET_CACHE.get("Dark", set())
    assert id(widget) not in _THEMED_WIDGET_CACHE.get("Light", set())

    widget.destroy()
    ctk.set_appearance_mode("light")
    should_apply_theme()
    # After mode change, cache should be cleared
    assert _THEMED_WIDGET_CACHE == {}


def test_should_apply_theme_clears_cache_on_mode_change(app_root):
    """should_apply_theme() should clear the cache when mode changes."""
    ctk.set_appearance_mode("dark")
    _THEMED_WIDGET_CACHE.clear()
    should_apply_theme()

    widget = ctk.CTkFrame(app_root)
    apply_form_theme(widget)
    assert id(widget) in _THEMED_WIDGET_CACHE.get("Dark", set())

    ctk.set_appearance_mode("light")
    should_apply_theme()
    assert _THEMED_WIDGET_CACHE == {}

    widget.destroy()
