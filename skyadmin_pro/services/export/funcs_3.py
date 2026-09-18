from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from openpyxl import Workbook

from ..importer.funcs import Database
from .funcs_0 import _atomic_excel_write, _plain_rows
from .funcs_1 import collect_export_payload
from .funcs_2 import write_excel_from_payload


def export_to_excel(
    db: Database,
    dest: Path,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    client_ids: list[int] | None = None,
    visible_only: dict[str, list[str]] | None = None,
    offload: bool = False,
) -> Path:
    """Export all sheets to Excel.

    visible_only maps sheet name → DB field names to keep (from the opt-in
    "visible columns only" checkbox). Sheets absent from the map, or whose
    filter would empty them, export complete — a sheet is never silently
    emptied. FORBIDDEN_EXPORT_COLUMNS never export regardless.

    When *offload* is True, openpyxl runs in a child process after DB
    queries complete in the parent (connections are never pickled).
    """
    payload = collect_export_payload(
        db,
        date_from=date_from,
        date_to=date_to,
        status=status,
        client_ids=client_ids,
        visible_only=visible_only,
    )
    if offload:
        from skyadmin_pro.services.process_jobs import run_in_process

        return Path(run_in_process(write_excel_from_payload, payload, str(dest)))
    return Path(write_excel_from_payload(payload, dest))


def collect_monthly_report_payload(db: Database, year: int, month: int) -> dict[str, Any]:
    """Gather monthly incentive rows + full export as a picklable payload."""
    rows = _plain_rows(db.list_incentive_services(year, month))
    columns = ["Date", "Client", "Service", "Source", "Amount"]
    records = []
    doc_total = 0.0
    for row in rows:
        service_date = (row.get("service_date") or "")[:10]
        amt = row.get("amount")
        src = "Document" if row.get("src") == "doc" else "Pipeline"
        if amt not in (None, "") and row.get("src") == "doc":
            doc_total += float(amt)
        records.append(
            {
                "Date": service_date or None,
                "Client": row.get("client_name") or "",
                "Service": row.get("service") or "",
                "Source": src,
                "Amount": amt if amt not in (None, "") else None,
            }
        )
    return {
        "monthly": {"columns": columns, "records": records, "total": doc_total},
        "full_export": collect_export_payload(db),
    }


def write_monthly_report_from_payload(payload: dict[str, Any], dest: str | Path) -> str:
    """Write monthly incentive Excel, followed by all full-export sheets."""
    monthly = payload.get("monthly") or {}
    columns = monthly.get("columns") or ["Date", "Client", "Service", "Source", "Amount"]
    records = monthly.get("records") or []
    total = monthly.get("total") or 0.0
    full_export = payload.get("full_export") or {}

    def build(target: Path) -> None:
        wb = Workbook(write_only=True)
        ws = wb.create_sheet(title="Incentive Report")
        ws.append(columns)
        for record in records:
            ws.append([record.get(col) for col in columns])
        if records:
            ws.append(["", "", "", "Document Total", total])

        # Delegate the rest of the sheets to the standard writer logic
        from .funcs_2 import append_full_export_sheets

        append_full_export_sheets(wb, full_export)

        wb.save(target)

    return str(_atomic_excel_write(build, Path(dest)))


def export_monthly_report(db: Database, year: int, month: int, dest: Path, *, offload: bool = False) -> Path:
    """Export the monthly incentive report (new signups) to Excel."""
    payload = collect_monthly_report_payload(db, year, month)
    if offload:
        from skyadmin_pro.services.process_jobs import run_in_process

        return Path(run_in_process(write_monthly_report_from_payload, payload, str(dest)))
    return Path(write_monthly_report_from_payload(payload, dest))


def default_export_name() -> str:
    return f"SkyAdminPro_Export_{date.today().strftime('%Y%m%d')}.xlsx"
