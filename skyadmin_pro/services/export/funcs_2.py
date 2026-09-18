from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import Workbook

from ._const_0 import _TASK_COLUMNS
from ._const_1 import _CLIENT_COLUMNS
from ._const_2 import _DOCUMENT_COLUMNS
from ._const_3 import _COURIER_COLUMNS
from ._const_4 import _SUPPLIER_COLUMNS
from ._const_5 import _SUPPLIER_PAYMENT_COLUMNS
from ._const_6 import _SUPPLIER_SERVICE_COLUMNS
from ._const_7 import _PIPELINE_COLUMNS
from ._const_8 import _RENEWAL_COLUMNS
from ._const_9 import _FINANCIAL_DOC_COLUMNS
from .funcs_0 import _atomic_excel_write, _ordered_keys, _sheet_rows


def write_excel_from_payload(payload: dict[str, Any], dest: str | Path) -> str:
    """Build the Excel workbook from a picklable payload. Returns dest as str."""
    tasks = payload.get("tasks") or []
    clients = payload.get("clients") or []
    documents = payload.get("documents") or []
    courier = payload.get("courier") or []
    suppliers = payload.get("suppliers") or []
    supplier_payments = payload.get("supplier_payments") or []
    supplier_services = payload.get("supplier_services") or []
    pipeline = payload.get("pipeline") or []
    renewals = payload.get("renewals") or []
    financial_docs = payload.get("financial_docs") or []
    visible_only = payload.get("visible_only")

    def build(target: Path) -> None:
        wb = Workbook(write_only=True)
        append_full_export_sheets(wb, payload)
        wb.save(target)

    return str(_atomic_excel_write(build, Path(dest)))


def append_full_export_sheets(wb: Workbook, payload: dict[str, Any]) -> None:
    """Append standard export sheets to the given workbook."""
    tasks = payload.get("tasks") or []
    clients = payload.get("clients") or []
    documents = payload.get("documents") or []
    courier = payload.get("courier") or []
    suppliers = payload.get("suppliers") or []
    supplier_payments = payload.get("supplier_payments") or []
    supplier_services = payload.get("supplier_services") or []
    pipeline = payload.get("pipeline") or []
    renewals = payload.get("renewals") or []
    financial_docs = payload.get("financial_docs") or []
    visible_only = payload.get("visible_only")

    def normalize_paid(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not records or "paid" not in _ordered_keys(records):
            return records
        return [
            {
                **r,
                "paid": "Yes"
                if r.get("paid") in (1, True)
                else ("No" if r.get("paid") in (0, False) else r.get("paid")),
            }
            for r in records
        ]

    def effective_mapping(sheet: str, mapping: dict[str, str]) -> dict[str, str]:
        if not visible_only or sheet not in visible_only:
            return mapping
        keep = [f for f in mapping if f in set(visible_only[sheet])]
        return {k: mapping[k] for k in keep} if keep else mapping

    payments = normalize_paid(supplier_payments)
    for sheet_name, records, mapping in (
        ("Tasks", tasks, _TASK_COLUMNS),
        ("Clients", clients, _CLIENT_COLUMNS),
        ("Documents", documents, _DOCUMENT_COLUMNS),
        ("Courier", courier, _COURIER_COLUMNS),
        ("Suppliers", suppliers, _SUPPLIER_COLUMNS),
        ("Supplier Payments", payments, _SUPPLIER_PAYMENT_COLUMNS),
        ("Supplier Services", supplier_services, _SUPPLIER_SERVICE_COLUMNS),
        ("Pipeline", pipeline, _PIPELINE_COLUMNS),
        ("Renewals", renewals, _RENEWAL_COLUMNS),
        ("Financial Docs", financial_docs, _FINANCIAL_DOC_COLUMNS),
    ):
        headers, rows = _sheet_rows(records, effective_mapping(sheet_name, mapping))
        ws = wb.create_sheet(title=sheet_name[:31])
        ws.append(headers)
        for row in rows:
            ws.append(row)
