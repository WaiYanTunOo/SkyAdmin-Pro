"""Excel fallback export for the offline SQLite database."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from skyadmin_pro.database import Database


def export_to_excel(db: Database, dest: Path) -> Path:
    import pandas as pd

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    tasks = db.list_tasks()
    clients = db.list_clients()
    documents = db.list_documents()
    courier = db.list_courier_logs()

    tasks_df = pd.DataFrame(tasks)
    clients_df = pd.DataFrame(clients)
    documents_df = pd.DataFrame(documents)
    courier_df = pd.DataFrame(courier)

    rename_maps = {
        "tasks": {
            "id": "ID",
            "client_name": "Client",
            "title": "Title",
            "description": "Description",
            "status": "Status",
            "category": "Category",
            "due_date": "Due date",
            "completed_at": "Completed at",
            "created_at": "Created at",
        },
        "clients": {
            "id": "ID",
            "name": "Name",
            "company_name": "Company",
            "notes": "Notes",
            "created_at": "Created at",
        },
        "documents": {
            "id": "ID",
            "client_name": "Client",
            "document_type": "Document type",
            "expiry_date": "Expiry date",
            "amount": "Amount",
            "file_name": "File name",
            "file_path": "File path",
            "created_at": "Created at",
        },
        "courier": {
            "id": "ID",
            "client_name": "Client",
            "task_title": "Related task",
            "tracking_number": "Tracking number",
            "driver_name": "Driver",
            "date_sent": "Date sent",
            "destination": "Destination",
            "notes": "Notes",
            "created_at": "Created at",
        },
    }

    def _sheet(frame: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
        if frame.empty:
            return pd.DataFrame(columns=list(mapping.values()))
        keep = [column for column in mapping if column in frame.columns]
        return frame[keep].rename(columns=mapping)

    with pd.ExcelWriter(dest, engine="openpyxl") as writer:
        _sheet(tasks_df, rename_maps["tasks"]).to_excel(writer, sheet_name="Tasks", index=False)
        _sheet(clients_df, rename_maps["clients"]).to_excel(writer, sheet_name="Clients", index=False)
        _sheet(documents_df, rename_maps["documents"]).to_excel(
            writer, sheet_name="Documents", index=False
        )
        _sheet(courier_df, rename_maps["courier"]).to_excel(
            writer, sheet_name="Courier", index=False
        )
    return dest


def default_export_name() -> str:
    return f"SkyAdminPro_Export_{date.today().strftime('%Y%m%d')}.xlsx"
