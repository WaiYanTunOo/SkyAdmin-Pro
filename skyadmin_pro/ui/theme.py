"""CustomTkinter theme tokens for SkyAdmin Pro — single source of truth.

All views should import from here instead of hard-coding sizes/colors.
"""

from __future__ import annotations

# Sidebar — tweaked for density / icons
SIDEBAR_WIDTH = 260
SIDEBAR_COLLAPSED_WIDTH = 56
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

# Surfaces — tab panes, scroll areas, cards (readable in light + dark)
SURFACE_BG = ("#e8e8e8", "#2b2b2b")
SCROLLABLE_BG = ("#f0f0f0", "#1e1e1e")
CARD_BG = ("#ebebeb", "#2b2b2b")
CONTENT_BG = ("#dbdbdb", "#242424")

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


def tabview_style_kwargs() -> dict:
    """CTkTabview colors that stay readable in light and dark mode."""
    return {
        "fg_color": SURFACE_BG,
        "segmented_button_fg_color": ("#d4d4d4", "#343638"),
        "segmented_button_selected_color": ACCENT,
        "segmented_button_selected_hover_color": ACCENT_HOVER,
        "segmented_button_unselected_color": ("#c8c8c8", "#4a4a4a"),
        "segmented_button_unselected_hover_color": ("#b8b8b8", "#565b5e"),
    }


def scrollable_style_kwargs() -> dict:
    return {"fg_color": SCROLLABLE_BG}


def card_style_kwargs() -> dict:
    return {"fg_color": CARD_BG}


def table_palette(mode: str) -> dict[str, str]:
    """ttk.Treeview colors for light/dark — used by ThemedTreeview."""
    if mode == "Dark":
        return {
            "background": "#1e1e1e",
            "foreground": "#e4e4e7",
            "heading": "#374151",
            "heading_fg": "#f9fafb",
            "fieldbackground": "#1e1e1e",
            "selected": "#1f538d",
            "odd": "#1e1e1e",
            "even": "#27272a",
            "scrollbar": "#4b5563",
            "trough": "#1e1e1e",
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
        "heading_fg": "#18181b",
        "fieldbackground": "#ffffff",
        "selected": "#3b8ed0",
        "odd": "#ffffff",
        "even": "#f4f4f5",
        "scrollbar": "#d4d4d8",
        "trough": "#f4f4f5",
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
