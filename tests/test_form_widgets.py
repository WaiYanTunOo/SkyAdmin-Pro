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
