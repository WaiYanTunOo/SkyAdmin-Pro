"""CustomTkinter theme tokens for SkyAdmin Pro — single source of truth.

All views should import from here instead of hard-coding sizes/colors.
"""

from __future__ import annotations

# Sidebar — tweaked for density / icons
SIDEBAR_WIDTH = 260
SIDEBAR_BUTTON_HEIGHT = 44
SIDEBAR_PADX = 16
SIDEBAR_PADY = 5
SIDEBAR_ACTIVE_BG = ("#2563eb", "#1e40af")
SIDEBAR_ACTIVE_TEXT = ("white", "white")
SIDEBAR_HOVER_BG = ("gray80", "gray25")
SIDEBAR_TEXT = ("gray10", "gray90")
SIDEBAR_ICONS = {
    "dashboard": "◧",
    "document_hub": "⧉",
    "database_tasks": "▦",
    "office_hub": "☎",
    "utilities": "✦",
    "settings": "⚙",
}

# Content — airier density
CONTENT_PAD = 24
HEADER_TITLE_SIZE = 22
HEADER_SUBTITLE_SIZE = 13

# Cards (used by Database & Tasks panels and the shared MonthStatusPanel)
CARD_RADIUS = 14
CARD_TITLE_SIZE = 16
CARD_TITLE_PADX = 18
CARD_TITLE_PADY_TOP = 16
CARD_CONTENT_PADX = 16
CARD_GAP = 16

# Typography scale (reuse instead of inline literals)
FONT_SIZE_XS = 11
FONT_SIZE_SM = 12
FONT_SIZE_MD = 13
FONT_SIZE_LG = 14
FONT_SIZE_XL = 16
FONT_SIZE_TITLE = 20
FONT_SIZE_HERO = 22

# Semantic text colors — accessible in both Light/Dark
TEXT_MUTED = ("gray40", "gray70")
TEXT_SUBTLE = ("gray45", "gray65")
TEXT_FAINT = ("gray50", "gray60")
TEXT_INVERSE = ("gray10", "gray90")

# Feedback — refined accent & accessible contrast
FEEDBACK_SUCCESS = ("#166534", "#4ade80")
FEEDBACK_ERROR = ("#b91c1c", "#f87171")
FEEDBACK_WARNING = ("#a16207", "#fbbf24")
FEEDBACK_INFO = TEXT_MUTED
ACCENT = ("#2563eb", "#3b82f6")
ACCENT_STRONG = ("#1d4ed8", "#1e40af")

# Status bar
STATUS_BAR_HEIGHT = 32

# Chart / canvas (tk.Canvas is not theme-aware by default)
CANVAS_BG = ("#f4f4f5", "#2b2b2b")
CANVAS_TEXT = ("#6b7280", "#9ca3af")
CANVAS_VALUE_TEXT = ("#111827", "#f4f4f5")

# Wrapping — prefer dynamic (bind <Configure>) over these, but they are
# the fallback when a label is created before layout.
WRAP_CARD = 760
WRAP_PREVIEW = 420
WRAP_TOOLBAR = 720

# Accent used for the active nav item and primary actions.
ACCENT_HOVER = ("#1e40af", "#1d4ed8")
TABLE_ROW_HEIGHT = 30
TABLE_FONT_SIZE = 10
TABLE_HEADER_FONT_SIZE = 10

# Form layout — label above field, consistent spacing (Phase 0)
FORM_ROW_GAP = 12
FORM_LABEL_GAP = 4
FORM_FIELD_HEIGHT = 36
FORM_SIDEBAR_MIN_WIDTH = 320
SECTION_GAP = 20
FORM_LABEL_COLOR = TEXT_INVERSE
FORM_LABEL_FONT_SIZE = FONT_SIZE_SM

# Input contrast — readable in light and dark (entries, combos, textboxes)
ENTRY_FG = ("#ffffff", "#1a1f2e")
ENTRY_BORDER = ("#94a3b8", "#5b6578")
ENTRY_TEXT = ("#111827", "#f3f4f6")
ENTRY_PLACEHOLDER = ("#6b7280", "#9ca3af")
TEXTBOX_FG = ENTRY_FG
TEXTBOX_BORDER = ENTRY_BORDER
TEXTBOX_TEXT = ENTRY_TEXT


def table_palette(mode: str) -> dict[str, str]:
    """ttk.Treeview colors for light/dark — used by ThemedTreeview."""
    if mode == "Dark":
        return {
            "background": "#2b2b2b",
            "foreground": "#f4f4f5",
            "heading": "#333333",
            "selected": "#1f538d",
            "odd": "#2b2b2b",
            "even": "#333333",
            "expired": "#7f1d1d",
            "urgent": "#9a3412",
            "watch": "#854d0e",
            "green": "#14532d",
            "yellow": "#a16207",
            "orange": "#9a3412",
            "red": "#7f1d1d",
            "done": "#14532d",
            "wip": "#78350f",
        }
    return {
        "background": "#ffffff",
        "foreground": "#18181b",
        "heading": "#e4e4e7",
        "selected": "#3b8ed0",
        "odd": "#ffffff",
        "even": "#f4f4f5",
        "expired": "#fecaca",
        "urgent": "#fed7aa",
        "watch": "#fde68a",
        "green": "#dcfce7",
        "yellow": "#fef08a",
        "orange": "#fed7aa",
        "red": "#fecaca",
        "done": "#dcfce7",
        "wip": "#fef3c7",
    }
