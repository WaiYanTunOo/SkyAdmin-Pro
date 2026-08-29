"""Wave C — discover accounting clients and infer Tax IDs contract fields."""

from __future__ import annotations

from typing import TYPE_CHECKING

from skyadmin_pro.config import (
    ACCOUNTING_SERVICE_INFER_PRIORITY,
    DOCUMENT_TO_ACCOUNTING_SERVICE,
)

if TYPE_CHECKING:
    from skyadmin_pro.database import Database


def parse_document_types(document_types: str | None) -> list[str]:
    if not document_types:
        return []
    return [part.strip() for part in str(document_types).split(",") if part.strip()]


def infer_service_type_from_documents(document_types: str | None) -> str | None:
    """Map tracked document types to an accounting contract service type."""
    matches = {
        DOCUMENT_TO_ACCOUNTING_SERVICE[doc]
        for doc in parse_document_types(document_types)
        if doc in DOCUMENT_TO_ACCOUNTING_SERVICE
    }
    for service_type in ACCOUNTING_SERVICE_INFER_PRIORITY:
        if service_type in matches:
            return service_type
    return None


def setup_missing_fields(client: dict) -> list[str]:
    """Human-readable list of Tax IDs fields still empty for an accounting client."""
    missing: list[str] = []
    if not (client.get("service_type") or "").strip():
        missing.append("Service type")
    if not (client.get("num_transactions") or "").strip():
        missing.append("Transaction volume")
    if not (client.get("tax_id") or "").strip():
        missing.append("Tax ID")
    return missing


def setup_status_label(missing: list[str]) -> str:
    if not missing:
        return "Ready"
    if len(missing) == 1:
        return "Almost"
    return "Needs setup"


def enrich_setup_row(row: dict) -> dict:
    """Add suggested service type and setup status to a database candidate row."""
    suggested = infer_service_type_from_documents(row.get("document_types"))
    missing = setup_missing_fields(row)
    return {
        **row,
        "suggested_service_type": suggested or "",
        "setup_missing": missing,
        "setup_status": setup_status_label(missing),
    }


def list_accounting_setup_rows(db: Database) -> list[dict]:
    return [enrich_setup_row(row) for row in db.list_accounting_setup_candidates()]


def apply_pricing_tier(db: Database, client_id: int) -> bool:
    """Fill fee, SLA, and headcount from the pricing matrix when possible."""
    client = db.get_client(client_id)
    if not client:
        return False
    service_type = (client.get("service_type") or "").strip()
    txn_range = (client.get("num_transactions") or "").strip()
    if not service_type or not txn_range:
        return False
    tier = db.lookup_pricing_by_range(txn_range, service_type=service_type)
    if not tier:
        return False
    fee = tier.get("monthly_fee")
    sla = tier.get("sla_hours")
    headcount = tier.get("headcount")
    db.update_client_fields(
        client_id,
        service_fee=str(fee) if fee is not None else "",
        sla=str(sla) if sla is not None else "",
        headcount=headcount,
    )
    return True


def infer_service_types(db: Database, *, only_missing: bool = True) -> int:
    """Infer and save service_type from tracked documents for accounting clients."""
    updated = 0
    for row in db.list_accounting_setup_candidates():
        if only_missing and (row.get("service_type") or "").strip():
            continue
        suggested = infer_service_type_from_documents(row.get("document_types"))
        if not suggested:
            continue
        db.update_client_fields(int(row["id"]), service_type=suggested)
        updated += 1
    return updated
