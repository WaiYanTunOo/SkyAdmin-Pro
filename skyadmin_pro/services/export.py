"""Excel fallback export for the offline SQLite database."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from skyadmin_pro.database import Database


def _sheet(frame, mapping: dict[str, str]):
    import pandas as pd

    if frame is None or frame.empty:
        return pd.DataFrame(columns=list(mapping.values()))
    keep = [column for column in mapping if column in frame.columns]
    return frame[keep].rename(columns=mapping)


def _atomic_excel_write(writer_builder, dest: Path) -> Path:
    """Build the workbook at a temp path, then atomically swap into place.

    If the destination is locked (open in Excel), no partial file is left
    behind and the original error surfaces to the caller.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.stem + ".partial" + dest.suffix)
    try:
        writer_builder(tmp)
        os.replace(tmp, dest)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return dest


def export_to_excel(db: Database, dest: Path) -> Path:
    import pandas as pd

    tasks = db.list_tasks()
    clients = db.list_clients()
    documents = db.list_documents()
    courier = db.list_courier_logs()
    suppliers = db.list_suppliers()
    supplier_payments = db.list_supplier_payments()
    supplier_services = db.list_all_supplier_services()
    pipeline = db.list_pipeline_items()
    renewals = db.all_service_renewals()
    financial_docs = db.all_financial_documents()

    def build(target: Path) -> None:
        payments_frame = pd.DataFrame(supplier_payments)
        if not payments_frame.empty and "paid" in payments_frame.columns:
            payments_frame = payments_frame.copy()
            payments_frame["paid"] = payments_frame["paid"].apply(
                lambda value: "Yes" if value in (1, True) else ("No" if value in (0, False) else value)
            )
        with pd.ExcelWriter(target, engine="openpyxl") as writer:
            for sheet_name, frame, mapping in (
                ("Tasks", pd.DataFrame(tasks), _TASK_COLUMNS),
                ("Clients", pd.DataFrame(clients), _CLIENT_COLUMNS),
                ("Documents", pd.DataFrame(documents), _DOCUMENT_COLUMNS),
                ("Courier", pd.DataFrame(courier), _COURIER_COLUMNS),
                ("Suppliers", pd.DataFrame(suppliers), _SUPPLIER_COLUMNS),
                ("Supplier Payments", payments_frame, _SUPPLIER_PAYMENT_COLUMNS),
                ("Supplier Services", pd.DataFrame(supplier_services), _SUPPLIER_SERVICE_COLUMNS),
                ("Pipeline", pd.DataFrame(pipeline), _PIPELINE_COLUMNS),
                ("Renewals", pd.DataFrame(renewals), _RENEWAL_COLUMNS),
                ("Financial Docs", pd.DataFrame(financial_docs), _FINANCIAL_DOC_COLUMNS),
            ):
                _sheet(frame, mapping).to_excel(writer, sheet_name=sheet_name[:31], index=False)

    return _atomic_excel_write(build, Path(dest))


_TASK_COLUMNS = {
    "id": "ID",
    "client_name": "Client",
    "title": "Title",
    "description": "Description",
    "status": "Status",
    "category": "Category",
    "due_date": "Due date",
    "completed_at": "Completed at",
    "created_at": "Created at",
}
_CLIENT_COLUMNS = {
    "id": "ID",
    "name": "Company name",
    "contact_name": "Contact",
    "email": "Email",
    "status": "Status",
    "company_name": "Company",
    "tax_id": "Tax ID",
    "service_type": "Service type",
    "service_fee": "Service fee",
    "notes": "Notes",
    "created_at": "Created at",
}
_DOCUMENT_COLUMNS = {
    "id": "ID",
    "client_name": "Client",
    "document_type": "Document type",
    "start_date": "Start date",
    "expiry_date": "Expiry date",
    "amount": "Amount",
    "payment_date": "Payment date",
    "progress": "Progress",
    "paid": "Paid",
    "file_name": "File name",
    "file_path": "File path",
    "created_at": "Created at",
}
_COURIER_COLUMNS = {
    "id": "ID",
    "client_name": "Client",
    "task_title": "Related task",
    "tracking_number": "Tracking number",
    "driver_name": "Driver",
    "date_sent": "Date sent",
    "destination": "Destination",
    "notes": "Notes",
    "created_at": "Created at",
}
_SUPPLIER_COLUMNS = {
    "id": "ID",
    "name": "Supplier",
    "company_name": "Company",
    "contact": "Contact",
    "notes": "Notes",
    "created_at": "Created at",
    "updated_at": "Updated at",
}
_SUPPLIER_PAYMENT_COLUMNS = {
    "id": "ID",
    "supplier_name": "Supplier",
    "client_name": "Client",
    "amount": "Amount",
    "due_date": "Due date",
    "paid_date": "Paid date",
    "paid": "Paid",
    "notes": "Notes",
}
_SUPPLIER_SERVICE_COLUMNS = {
    "supplier_name": "Supplier",
    "company_name": "Company",
    "service_type": "Service",
    "expiry_date": "Expiry date",
    "notes": "Notes",
}
_PIPELINE_COLUMNS = {
    "id": "ID",
    "client_name": "Client",
    "service": "Service",
    "step": "Step",
    "status": "Status",
    "created_at": "Created at",
}
_RENEWAL_COLUMNS = {
    "client_name": "Client",
    "document_type": "Service",
    "previous_expiry": "Previous expiry",
    "new_expiry": "New expiry",
    "renewed_at": "Renewed at",
}
_FINANCIAL_DOC_COLUMNS = {
    "id": "ID",
    "client_name": "Client",
    "category": "Category",
    "subcategory": "From",
    "file_name": "File name",
    "amount": "Amount",
    "doc_date": "Date",
    "description": "Description",
}


def export_monthly_report(db: Database, year: int, month: int, dest: Path) -> Path:
    """Export the monthly incentive report (new signups) to Excel."""
    import pandas as pd

    rows = db.list_incentive_services(year, month)
    mapping = {
        "client_name": "Client",
        "service": "Service",
        "amount": "Amount",
        "service_date": "Start date",
        "source": "Source",
    }

    def build(target: Path) -> None:
        df = pd.DataFrame(rows)
        if df.empty:
            df = pd.DataFrame(columns=list(mapping.values()))
        else:
            keep = [col for col in mapping if col in df.columns]
            df = df[keep].rename(columns=mapping)
            df["Source"] = df["Source"].map({"doc": "Document", "pipe": "Pipeline"}).fillna(df["Source"])
        with pd.ExcelWriter(target, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Incentive services", index=False)

    return _atomic_excel_write(build, Path(dest))


def default_export_name() -> str:
    return f"SkyAdminPro_Export_{date.today().strftime('%Y%m%d')}.xlsx"
