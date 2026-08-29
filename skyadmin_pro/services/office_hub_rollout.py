"""Wave D — Office Hub migration: contacts and portal logins per client."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skyadmin_pro.database import Database


def office_setup_missing(row: dict) -> list[str]:
    """Human-readable gaps for one client's Office Hub setup."""
    missing: list[str] = []
    contact_count = int(row.get("contact_count") or 0)
    credential_count = int(row.get("credential_count") or 0)
    rd_count = int(row.get("rd_count") or 0)
    has_legacy = int(row.get("has_legacy_ird") or 0)

    if contact_count == 0:
        if row.get("director") or row.get("contact_name") or row.get("email"):
            missing.append("Liaison contact")
        else:
            missing.append("Contact")
    if credential_count == 0:
        missing.append("Portal login")
    if has_legacy and rd_count == 0:
        missing.append("IRD migrate")
    return missing


def office_setup_status_label(missing: list[str]) -> str:
    if not missing:
        return "Ready"
    if len(missing) == 1:
        return "Almost"
    return "Needs setup"


def enrich_office_setup_row(row: dict) -> dict:
    missing = office_setup_missing(row)
    return {
        **row,
        "setup_missing": missing,
        "setup_status": office_setup_status_label(missing),
        "can_seed_contact": bool(
            int(row.get("contact_count") or 0) == 0 and ((row.get("director") or row.get("contact_name") or "").strip())
        ),
    }


def list_office_setup_rows(db: Database) -> list[dict]:
    return [enrich_office_setup_row(row) for row in db.list_office_hub_setup_candidates()]


def seed_liaison_contacts(db: Database, *, only_missing: bool = True, client_id: int | None = None) -> int:
    return db.seed_client_liaison_contacts(only_missing=only_missing, client_id=client_id)


def migrate_legacy_ird_passwords(db: Database) -> int:
    return db._migrate_ird_to_client_credentials()
