"""Status PDF reports — model assembly, redaction guard, rendering."""

from __future__ import annotations

import pytest

from skyadmin_pro.services.pdf_render import render_report, sanitize_pdf_text
from skyadmin_pro.services.reports import (
    REPORT_TABLE_ROW_CAP,
    _assert_no_forbidden,
    build_status_report,
)


def _seed_clients(db, count: int) -> None:
    with db.connection() as conn:
        conn.executemany(
            "INSERT INTO clients (name, contact_name, email, status) VALUES (?, ?, ?, ?)",
            [(f"Report Co {i:03d}", f"Contact {i}", f"r{i}@example.com", "active") for i in range(count)],
        )


def test_model_has_all_sections(db):
    _seed_clients(db, 3)
    model = build_status_report(db)
    assert model["title"].startswith("SkyAdmin Pro")
    assert model["generated_at"] and model["app_version"]
    assert ("Clients", "3") in model["summary"]
    titles = [s["title"] for s in model["sections"]]
    assert titles == [
        "Expiring documents",
        "Overdue services",
        "Pending tasks",
        "Renewals due",
        "Clients",
    ]
    clients = next(s for s in model["sections"] if s["title"] == "Clients")
    assert len(clients["rows"]) == 3
    assert clients["rows"][0][0] == "Report Co 000"


def test_forbidden_guard_rejects_poisoned_model():
    with pytest.raises(ValueError, match="forbidden key"):
        _assert_no_forbidden({"rows": [{"ird_password": "x"}]})
    # Real model passes the same scan.
    _assert_no_forbidden({"title": "ok", "rows": [[1, 2]]})


def test_table_row_cap(db):
    _seed_clients(db, REPORT_TABLE_ROW_CAP + 5)
    model = build_status_report(db)
    clients = next(s for s in model["sections"] if s["title"] == "Clients")
    assert len(clients["rows"]) == REPORT_TABLE_ROW_CAP
    assert str(REPORT_TABLE_ROW_CAP + 5) in clients["note"]


def test_render_produces_readable_pdf(db, tmp_path):
    _seed_clients(db, 2)
    dest = tmp_path / "report.pdf"
    out = render_report(build_status_report(db), dest)
    assert out.is_file()
    assert out.read_bytes()[:5] == b"%PDF-"
    from pypdf import PdfReader

    reader = PdfReader(str(out))
    assert len(reader.pages) >= 1
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "SkyAdmin Pro" in text
    assert "Report Co 000" in text
    assert "ird_password" not in text.lower()


def test_sanitize_pdf_text_replaces_non_latin():
    assert sanitize_pdf_text("Acme Co") == "Acme Co"
    assert "?" in sanitize_pdf_text("บริษัท ทดสอบ")
