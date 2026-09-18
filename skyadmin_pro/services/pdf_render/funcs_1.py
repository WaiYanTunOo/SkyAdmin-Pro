from __future__ import annotations

import os

from ._const_0 import sanitize_pdf_text


def _render_report_p2(fonts, model, pdf, dest):
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
