"""Process-pool offload helpers for export/PDF."""

from pathlib import Path

from skyadmin_pro.services import process_jobs
from skyadmin_pro.services.export import write_excel_from_payload
from skyadmin_pro.services.pdf_render import render_report_offloaded


def test_run_in_process_echo():
    assert process_jobs.run_in_process(process_jobs._echo, "ok") == "ok"


def test_write_excel_from_payload_roundtrip(tmp_path):
    dest = tmp_path / "out.xlsx"
    payload = {
        "tasks": [],
        "clients": [{"id": 1, "name": "Acme", "status": "active"}],
        "documents": [],
        "courier": [],
        "suppliers": [],
        "supplier_payments": [],
        "supplier_services": [],
        "pipeline": [],
        "renewals": [],
        "financial_docs": [],
        "visible_only": None,
    }
    out = Path(write_excel_from_payload(payload, dest))
    assert out.exists()
    assert out.stat().st_size > 0


def test_render_report_offloaded(tmp_path, monkeypatch):
    monkeypatch.setenv("SKYADMIN_PROCESS_OFFLOAD", "1")
    dest = tmp_path / "report.pdf"
    model = {
        "title": "Test Report",
        "generated_at": "2026-01-01 00:00",
        "app_version": "0.0.0",
        "summary": [("Clients", "1")],
        "sections": [{"title": "Empty", "headers": ["A"], "rows": [], "note": ""}],
    }
    out = render_report_offloaded(model, dest)
    assert out.exists()
    assert out.stat().st_size > 0
