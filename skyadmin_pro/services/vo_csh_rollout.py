"""VO / CSH renewal date rollout — infer from tracked documents."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from skyadmin_pro.config import CSH_DOCUMENT_TYPES, VO_DOCUMENT_TYPES
from skyadmin_pro.services.tracking import effective_expiry_date

if TYPE_CHECKING:
    from skyadmin_pro.database import Database


def _latest_expiry_for_types(db: Database, client_id: int, doc_types: tuple[str, ...]) -> str | None:
    best: date | None = None
    for doc in db.list_client_services(client_id):
        if (doc.get("document_type") or "") not in doc_types:
            continue
        effective = effective_expiry_date(doc.get("expiry_date"), doc.get("document_type"))
        if not effective:
            continue
        try:
            parsed = date.fromisoformat(str(effective)[:10])
        except ValueError:
            continue
        if best is None or parsed > best:
            best = parsed
    return best.isoformat() if best else None


def suggested_vo_renewal_date(db: Database, client_id: int) -> str | None:
    return _latest_expiry_for_types(db, client_id, VO_DOCUMENT_TYPES)


def suggested_csh_renewal_date(db: Database, client_id: int) -> str | None:
    return _latest_expiry_for_types(db, client_id, CSH_DOCUMENT_TYPES)


def vo_csh_setup_missing(row: dict) -> list[str]:
    missing: list[str] = []
    if int(row.get("vo_doc_count") or 0) > 0 and not (row.get("vo_renewal_date") or "").strip():
        missing.append("VO renewal")
    if int(row.get("csh_doc_count") or 0) > 0 and not (row.get("csh_renewal_date") or "").strip():
        missing.append("CSH renewal")
    return missing


def vo_csh_setup_status_label(missing: list[str]) -> str:
    if not missing:
        return "Ready"
    if len(missing) == 1:
        return "Almost"
    return "Needs setup"


def enrich_vo_csh_setup_row(db: Database, row: dict) -> dict:
    client_id = int(row["id"])
    suggested_vo = suggested_vo_renewal_date(db, client_id)
    suggested_csh = suggested_csh_renewal_date(db, client_id)
    missing = vo_csh_setup_missing(row)
    return {
        **row,
        "suggested_vo_renewal_date": suggested_vo or "",
        "suggested_csh_renewal_date": suggested_csh or "",
        "setup_missing": missing,
        "setup_status": vo_csh_setup_status_label(missing),
        "can_infer_vo": bool(not (row.get("vo_renewal_date") or "").strip() and suggested_vo),
        "can_infer_csh": bool(not (row.get("csh_renewal_date") or "").strip() and suggested_csh),
    }


def list_vo_csh_setup_rows(db: Database) -> list[dict]:
    return [enrich_vo_csh_setup_row(db, row) for row in db.list_vo_csh_setup_candidates()]


def infer_vo_csh_renewal_dates(db: Database, *, only_missing: bool = True) -> dict[str, int]:
    """Copy latest document expiry into client VO/CSH renewal fields."""
    vo_updated = 0
    csh_updated = 0
    for row in db.list_vo_csh_setup_candidates():
        client_id = int(row["id"])
        if only_missing and not (row.get("vo_renewal_date") or "").strip():
            vo_date = suggested_vo_renewal_date(db, client_id)
            if vo_date:
                db.update_client_fields(client_id, vo_renewal_date=vo_date)
                db.create_vo_csh_renewal(client_id, "vo", vo_date)
                vo_updated += 1
        if only_missing and not (row.get("csh_renewal_date") or "").strip():
            csh_date = suggested_csh_renewal_date(db, client_id)
            if csh_date:
                db.update_client_fields(client_id, csh_renewal_date=csh_date)
                db.create_vo_csh_renewal(client_id, "csh", csh_date)
                csh_updated += 1
    return {"vo": vo_updated, "csh": csh_updated}


def infer_client_vo_csh_renewal_dates(db: Database, client_id: int, *, only_missing: bool = True) -> dict[str, int]:
    """Infer renewal dates for one client."""
    row = db.get_client(client_id)
    if not row:
        return {"vo": 0, "csh": 0}
    vo_updated = csh_updated = 0
    if only_missing and not (row.get("vo_renewal_date") or "").strip():
        vo_date = suggested_vo_renewal_date(db, client_id)
        if vo_date:
            db.update_client_fields(client_id, vo_renewal_date=vo_date)
            db.create_vo_csh_renewal(client_id, "vo", vo_date)
            vo_updated = 1
    if only_missing and not (row.get("csh_renewal_date") or "").strip():
        csh_date = suggested_csh_renewal_date(db, client_id)
        if csh_date:
            db.update_client_fields(client_id, csh_renewal_date=csh_date)
            db.create_vo_csh_renewal(client_id, "csh", csh_date)
            csh_updated = 1
    return {"vo": vo_updated, "csh": csh_updated}
