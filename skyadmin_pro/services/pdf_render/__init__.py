"""PDF rendering for status reports — fpdf2, core fonts, English-only.

Font strategy (v1): Helvetica core fonts (latin-1, always available, zero
bundle cost). Non-latin text is sanitized to "?" via sanitize_pdf_text().
To add Thai later: embed a TTF (e.g. Noto Sans Thai) and extend ReportFonts
with a regular/bold TTF pair — the renderer only uses fonts.* names.
"""

from __future__ import annotations

from ._const_0 import FONTS, ReportFonts, sanitize_pdf_text
from .funcs_0 import render_report, render_report_offloaded

__all__ = [
    "FONTS",
    "ReportFonts",
    "render_report",
    "render_report_offloaded",
    "sanitize_pdf_text",
]
