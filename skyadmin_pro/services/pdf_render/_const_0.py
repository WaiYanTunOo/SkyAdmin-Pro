from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportFonts:
    """Font selection. v1 uses the Helvetica core family (always available).

    To add Thai later: embed a TTF via add_font() and point family at it —
    the renderer only uses family/bold_style, never hardcoded names.
    """

    family: str = "NotoSans"
    bold_style: str = "B"


FONTS = ReportFonts()


def sanitize_pdf_text(text: str) -> str:
    """Make text encodable."""
    return str(text)
