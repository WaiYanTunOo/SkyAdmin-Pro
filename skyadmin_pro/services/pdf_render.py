"""PDF rendering for status reports — fpdf2, core fonts, English-only.

Font strategy (v1): Helvetica core fonts (latin-1, always available, zero
bundle cost). Non-latin text is sanitized to "?" via sanitize_pdf_text().
To add Thai later: embed a TTF (e.g. Noto Sans Thai) and extend ReportFonts
with a regular/bold TTF pair — the renderer only uses fonts.* names.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReportFonts:
    """Font selection. v1 uses the Helvetica core family (always available).

    To add Thai later: embed a TTF via add_font() and point family at it —
    the renderer only uses family/bold_style, never hardcoded names.
    """

    family: str = "helvetica"
    bold_style: str = "B"


FONTS = ReportFonts()


def sanitize_pdf_text(text: str) -> str:
    """Make text encodable in latin-1 core fonts (v1 English-only contract)."""
    return str(text).encode("latin-1", "replace").decode("latin-1")


def render_report(model: dict, dest: Path, *, fonts: ReportFonts = FONTS) -> Path:
    """Render a build_status_report() model to PDF (atomic write)."""
    from fpdf import FPDF

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(True, margin=15)
    pdf.set_title(sanitize_pdf_text(model.get("title", "Report")))
    pdf.add_page()

    pdf.set_font(fonts.family, fonts.bold_style, size=16)
    pdf.cell(0, 10, sanitize_pdf_text(model.get("title", "Report")), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fonts.family, size=9)
    pdf.set_text_color(110, 110, 110)
    pdf.cell(
        0,
        6,
        sanitize_pdf_text(f"Generated {model.get('generated_at', '')}  |  {model.get('app_version', '')}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # KPI summary — two-column label/value table.
    pdf.set_font(fonts.family, fonts.bold_style, size=12)
    pdf.cell(0, 8, "Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fonts.family, size=10)
    for label, value in model.get("summary", []):
        pdf.cell(70, 6, sanitize_pdf_text(label))
        pdf.cell(0, 6, sanitize_pdf_text(value), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    for section in model.get("sections", []):
        headers = [sanitize_pdf_text(h) for h in section.get("headers", [])]
        rows = [[sanitize_pdf_text(c) for c in row] for row in section.get("rows", [])]
        pdf.set_font(fonts.family, fonts.bold_style, size=12)
        pdf.cell(0, 8, sanitize_pdf_text(f"{section.get('title', '')} ({len(rows)})"), new_x="LMARGIN", new_y="NEXT")
        if not rows:
            pdf.set_font(fonts.family, size=10)
            pdf.cell(0, 6, "No items.", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            continue
        col_count = len(headers)
        usable = pdf.w - pdf.l_margin - pdf.r_margin
        col_w = usable / col_count
        pdf.set_font(fonts.family, fonts.bold_style, size=9)
        pdf.set_fill_color(230, 230, 230)
        for header in headers:
            pdf.cell(col_w, 7, header, border=1, fill=True)
        pdf.ln()
        pdf.set_font(fonts.family, size=9)
        pdf.set_fill_color(255, 255, 255)
        for row in rows:
            # Paginate before a row that would overflow.
            if pdf.get_y() > pdf.h - 25:
                pdf.add_page()
            cells = list(row) + [""] * (col_count - len(row))
            for cell in cells[:col_count]:
                pdf.cell(col_w, 6, cell, border=1)
            pdf.ln()
        note = section.get("note", "")
        if note:
            pdf.set_font(fonts.family, size=8)
            pdf.set_text_color(110, 110, 110)
            pdf.cell(0, 6, sanitize_pdf_text(note), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    tmp = dest.with_name(dest.stem + ".partial" + dest.suffix)
    try:
        pdf.output(str(tmp))
        os.replace(tmp, dest)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return dest


def _render_report_worker(model: dict, dest: str) -> str:
    """Picklable worker entry for process offload."""
    return str(render_report(model, Path(dest)))


def render_report_offloaded(model: dict, dest: Path) -> Path:
    """Render PDF in a child process (model must be picklable plain data)."""
    from skyadmin_pro.services.process_jobs import run_in_process

    return Path(run_in_process(_render_report_worker, model, str(dest)))
