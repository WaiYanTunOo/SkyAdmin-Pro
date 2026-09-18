from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..importer.funcs import Database
from ._const_0 import REPORT_TABLE_ROW_CAP
from ._const_1 import _TAX_OVERVIEW_KEYS
from .funcs_0 import _assert_no_forbidden, _cell, _project


def build_status_report(db: Database) -> dict:
    """Assemble the dashboard + tax snapshot status report model."""
    from skyadmin_pro.config import APP_VERSION

    snap = db.dashboard_snapshot()
    counts = snap.get("counts", {})

    summary: list[tuple[str, str]] = [
        ("Clients", _cell(counts.get("clients"))),
        ("Pending tasks", _cell(counts.get("pending"))),
        ("Completed today", _cell(counts.get("completed_today"))),
        ("Expiring soon", _cell(counts.get("expiring"))),
        ("Overdue", _cell(counts.get("overdue"))),
        ("Supplier payments due", _cell(counts.get("supplier_due"))),
        ("Ongoing services", _cell(counts.get("ongoing"))),
        ("Pending filings", _cell(snap.get("pending_filings"))),
    ]

    sections: list[dict] = []

    def add_section(title: str, headers: list[str], rows: list[list[str]]) -> None:
        total = len(rows)
        capped = rows[:REPORT_TABLE_ROW_CAP]
        note = f"Showing {len(capped)} of {total}." if total > len(capped) else ""
        sections.append({"title": title, "headers": headers, "rows": capped, "note": note})

    add_section(
        "Expiring documents",
        ["Client", "Type", "Expiry"],
        [_project(r, ("client_name", "document_type", "expiry_date")) for r in snap.get("expiring", [])],
    )
    add_section(
        "Overdue services",
        ["Client", "Type", "Payment due"],
        [_project(r, ("client_name", "document_type", "payment_date")) for r in snap.get("overdue", [])],
    )
    add_section(
        "Pending tasks",
        ["Title", "Client", "Category", "Due"],
        [_project(r, ("title", "client_name", "category", "due_date")) for r in snap.get("pending", [])],
    )
    add_section(
        "Renewals due",
        ["Client", "Template", "Service", "Days left"],
        [
            _project(r, ("client_name", "template_name", "document_type", "days_left"))
            for r in snap.get("renewal_due", [])
        ],
    )
    add_section(
        "Tax filing overview",
        [
            "Client",
            "PND1",
            "PND3",
            "PND53",
            "PP30",
            "PND90",
            "PND91",
            "PND50",
            "PND51",
            "FS",
            "Audit",
            "Payment",
        ],
        [_project(r, _TAX_OVERVIEW_KEYS) for r in snap.get("accounting_clients", [])],
    )
    clients = db.search_clients("")
    add_section(
        "Clients",
        ["Name", "Contact", "Email", "Status"],
        [_project(r, ("name", "contact_name", "email", "status")) for r in clients],
    )

    model = {
        "title": "SkyAdmin Pro — Status Report",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "app_version": APP_VERSION,
        "summary": summary,
        "sections": sections,
    }
    _assert_no_forbidden(model)
    return model


def write_status_report_pdf(db: Database, dest: Path, *, offload: bool = False) -> Path:
    """Build a redacted status report and render it to ``dest`` (atomic write)."""
    from skyadmin_pro.services.pdf_render import render_report, render_report_offloaded

    model = build_status_report(db)
    if offload:
        return render_report_offloaded(model, Path(dest))
    return render_report(model, Path(dest))


def default_report_name() -> str:
    return f"SkyAdminPro_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
