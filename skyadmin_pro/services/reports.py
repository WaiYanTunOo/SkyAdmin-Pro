"""Status report model — dashboard + Database & Tasks, English-only, redaction-safe.

The model is plain data (dicts/lists/strings) so the PDF renderer stays dumb.
Every row is projected through an explicit allowlist; a runtime assert scan
rejects forbidden columns (mirrors export.FORBIDDEN_EXPORT_COLUMNS).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skyadmin_pro.database import Database

from skyadmin_pro.services.export import FORBIDDEN_EXPORT_COLUMNS

#: Max rows per section table — keeps PDFs sane at 500+ clients.
REPORT_TABLE_ROW_CAP = 60


def _cell(value: object) -> str:
    if value is None:
        return "—"
    text = str(value).strip()
    return text if text else "—"


def _project(row: dict, keys: tuple[str, ...]) -> list[str]:
    return [_cell(row.get(key)) for key in keys]


def _assert_no_forbidden(model: dict) -> None:
    """Defense in depth: no forbidden column name may appear in keys or values."""

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if str(key).lower() in FORBIDDEN_EXPORT_COLUMNS:
                    raise ValueError(f"Refusing report — forbidden key: {key}")
                walk(value)
        elif isinstance(node, (list, tuple)):
            for item in node:
                walk(item)

    walk(model)


def build_status_report(db: Database) -> dict:
    """Assemble the dashboard + Database & Tasks status report model."""
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
        [
            _project(r, ("client_name", "document_type", "expiry_date"))
            for r in snap.get("expiring", [])
        ],
    )
    add_section(
        "Overdue services",
        ["Client", "Type", "Payment due"],
        [
            _project(r, ("client_name", "document_type", "payment_date"))
            for r in snap.get("overdue", [])
        ],
    )
    add_section(
        "Pending tasks",
        ["Title", "Client", "Category", "Due"],
        [
            _project(r, ("title", "client_name", "category", "due_date"))
            for r in snap.get("pending", [])
        ],
    )
    add_section(
        "Renewals due",
        ["Client", "Template", "Service", "Days left"],
        [
            _project(r, ("client_name", "template_name", "document_type", "days_left"))
            for r in snap.get("renewal_due", [])
        ],
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


def default_report_name() -> str:
    return f"SkyAdminPro_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
