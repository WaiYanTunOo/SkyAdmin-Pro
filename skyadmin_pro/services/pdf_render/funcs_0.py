from __future__ import annotations

from pathlib import Path

from ._const_0 import FONTS, ReportFonts, sanitize_pdf_text
from .funcs_1 import _render_report_p2


def render_report(model: dict, dest: Path, *, fonts: ReportFonts = FONTS) -> Path:
    """Render a build_status_report() model to PDF (atomic write)."""
    dest, pdf = _render_report_p1(dest, model, fonts)
    _render_report_p2(fonts, model, pdf, dest)
    return dest


def _render_report_worker(model: dict, dest: str) -> str:
    """Picklable worker entry for process offload."""
    return str(render_report(model, Path(dest)))


def render_report_offloaded(model: dict, dest: Path) -> Path:
    """Render PDF in a child process (model must be picklable plain data)."""
    from skyadmin_pro.services.process_jobs import run_in_process

    return Path(run_in_process(_render_report_worker, model, str(dest)))


def _render_report_p1(dest, model, fonts):
    from fpdf import FPDF

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(True, margin=15)

    font_dir = Path(__file__).parent.parent.parent / "assets" / "fonts"
    if font_dir.exists():
        pdf.add_font("NotoSans", "", str(font_dir / "NotoSans-Regular.ttf"))
        pdf.add_font("NotoSans", "B", str(font_dir / "NotoSans-Bold.ttf"))
        pdf.add_font("NotoSansThai", "", str(font_dir / "NotoSansThai-Regular.ttf"))
        pdf.add_font("NotoSansThai", "B", str(font_dir / "NotoSansThai-Bold.ttf"))
        pdf.add_font("NotoSansMyanmar", "", str(font_dir / "NotoSansMyanmar-Regular.ttf"))
        pdf.add_font("NotoSansMyanmar", "B", str(font_dir / "NotoSansMyanmar-Bold.ttf"))
        pdf.set_fallback_fonts(["NotoSansThai", "NotoSansMyanmar"])
        pdf.set_text_shaping(True)

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
    return dest, pdf
