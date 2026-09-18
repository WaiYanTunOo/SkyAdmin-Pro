"""Phase 0 form widgets — styling helpers (no extra Tk roots)."""

from skyadmin_pro.ui.theme import ENTRY_FG, ENTRY_TEXT, FORM_FIELD_HEIGHT
from skyadmin_pro.ui.widgets import combo_style_kwargs, entry_style_kwargs


def test_entry_style_kwargs_contrast():
    kwargs = entry_style_kwargs()
    assert kwargs["height"] == FORM_FIELD_HEIGHT
    assert kwargs["fg_color"] == ENTRY_FG
    assert kwargs["text_color"] == ENTRY_TEXT
    assert kwargs["border_width"] == 1
    assert "placeholder_text_color" in kwargs


def test_combo_style_omits_placeholder():
    kwargs = combo_style_kwargs()
    assert "placeholder_text_color" not in kwargs
    assert kwargs["fg_color"] == ENTRY_FG


def test_apply_form_theme_gc_safe_caching():
    import customtkinter as ctk

    from skyadmin_pro.ui.widgets import apply_form_theme

    class MockWidget:
        def __init__(self, children=None):
            self._children = children or []

        def winfo_children(self):
            return list(self._children)

    child = MockWidget()
    parent = MockWidget([child])

    current_mode = ctk.get_appearance_mode()
    apply_form_theme(parent)

    assert getattr(parent, "_subtree_themed_mode", None) == current_mode
    assert getattr(parent, "_applied_form_theme_mode", None) == current_mode
    assert getattr(child, "_subtree_themed_mode", None) == current_mode
    assert getattr(child, "_applied_form_theme_mode", None) == current_mode

    # Subsequent call with same mode should return early on subtree check
    call_count = 0
    original_winfo = parent.winfo_children

    def counted_winfo():
        nonlocal call_count
        call_count += 1
        return original_winfo()

    parent.winfo_children = counted_winfo
    apply_form_theme(parent)
    assert call_count == 0  # skipped walk completely!


def test_should_apply_theme_transitions():
    import skyadmin_pro.ui.widgets as w

    # Initial state
    w._LAST_THEME_MODE = None
    assert w.should_apply_theme() is True
    assert w.should_apply_theme() is False
