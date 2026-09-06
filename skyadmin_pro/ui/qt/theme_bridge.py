"""Map CustomTkinter theme tokens (ui/theme.py) onto Qt (Phase 3 shell).

Tokens in ``theme.py`` are ``(light, dark)`` tuples or plain constants.
This bridge resolves them per appearance mode so the Qt shell and the
CustomTkinter app share one source of truth instead of forked palettes.
"""

from __future__ import annotations

from typing import Any

from skyadmin_pro.ui import theme as tokens

DARK = "dark"
LIGHT = "light"


def normalize_mode(mode: str | None) -> str:
    """Fold appearance settings into 'dark' or 'light' (system -> light)."""
    text = str(mode or "").strip().lower()
    if text.startswith("dark"):
        return DARK
    return LIGHT


def resolve(token: Any, mode: str) -> Any:
    """Resolve one theme token for *mode*.

    Token pairs are (light, dark) — e.g. SIDEBAR_TEXT ("gray10", "gray90").
    Plain constants pass through untouched.
    """
    if isinstance(token, (tuple, list)) and len(token) == 2:
        return token[1] if normalize_mode(mode) == DARK else token[0]
    return token


def palette(mode: str) -> dict[str, Any]:
    """Core surface/accent/text colors for *mode* as plain values."""
    return {
        "surface": resolve(tokens.SURFACE_BG, mode),
        "content": resolve(tokens.CONTENT_BG, mode),
        "card": resolve(tokens.CARD_BG, mode),
        "scrollable": resolve(tokens.SCROLLABLE_BG, mode),
        "accent": resolve(tokens.ACCENT, mode),
        "accent_strong": resolve(tokens.ACCENT_STRONG, mode),
        "sidebar_text": resolve(tokens.SIDEBAR_TEXT, mode),
        "sidebar_active_bg": resolve(tokens.SIDEBAR_ACTIVE_BG, mode),
        "text_muted": resolve(tokens.TEXT_MUTED, mode),
        "success": resolve(tokens.FEEDBACK_SUCCESS, mode),
        "error": resolve(tokens.FEEDBACK_ERROR, mode),
        "warning": resolve(tokens.FEEDBACK_WARNING, mode),
        "canvas_bg": resolve(tokens.CANVAS_BG, mode),
        "canvas_text": resolve(tokens.CANVAS_TEXT, mode),
    }


def fonts() -> dict[str, int]:
    """Typography scale shared with the CustomTkinter app."""
    return {
        "xs": tokens.FONT_SIZE_XS,
        "sm": tokens.FONT_SIZE_SM,
        "md": tokens.FONT_SIZE_MD,
        "lg": tokens.FONT_SIZE_LG,
        "xl": tokens.FONT_SIZE_XL,
        "title": tokens.FONT_SIZE_TITLE,
        "hero": tokens.FONT_SIZE_HERO,
    }


def apply_theme(app, mode: str) -> dict[str, Any]:
    """Apply Fusion + resolved palette to a QApplication. Returns the palette."""
    from PySide6.QtWidgets import QApplication, QStyleFactory

    pal = palette(mode)
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setStyleSheet(
        f"""
        QMainWindow, QWidget#qt-shell-central {{ background: {pal["content"]}; }}
        QListWidget#qt-shell-nav {{
            background: {pal["surface"]}; border: none;
            font-size: {tokens.FONT_SIZE_MD}pt;
        }}
        QListWidget#qt-shell-nav::item {{ padding: 10px 12px; color: {pal["sidebar_text"]}; }}
        QListWidget#qt-shell-nav::item:selected {{
            background: {pal["accent"]}; color: white; border-radius: 6px;
        }}
        QStatusBar#qt-shell-status {{ background: {pal["surface"]}; color: {pal["text_muted"]}; }}
        QLabel#qt-shell-title {{ font-size: {tokens.FONT_SIZE_TITLE}pt; font-weight: 600; }}
        QLabel#qt-shell-subtitle {{ font-size: {tokens.FONT_SIZE_SM}pt; color: {pal["text_muted"]}; }}
        QPushButton#qt-shell-accent {{
            background: {pal["accent"]}; color: white; border: none;
            border-radius: 6px; padding: 8px 16px;
        }}
        """
    )
    if isinstance(app, QApplication):
        app.setApplicationDisplayName("SkyAdmin Pro")
    return pal
