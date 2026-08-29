"""One-shot database + workspace cleanup after restore or upgrade."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from skyadmin_pro.services.office_hub_rollout import migrate_legacy_ird_passwords, seed_liaison_contacts
from skyadmin_pro.services.tax_ids_rollout import infer_service_types
from skyadmin_pro.services.vo_csh_rollout import infer_vo_csh_renewal_dates
from skyadmin_pro.services.workflow import repair_client_workspaces

if TYPE_CHECKING:
    from skyadmin_pro.database import Database


def run_data_hygiene(db: Database, clients_root: Path) -> dict[str, int | list[str]]:
    """Refresh pricing, directories, folders, and rolled annual expiry dates."""
    db._seed_all_service_pricing()
    new_clients, new_depts = db.import_directory_from_data()
    folder_result = repair_client_workspaces(clients_root, db.list_client_names())
    expiry_rolled = db.roll_forward_stale_expiry_dates()
    ird_migrated = migrate_legacy_ird_passwords(db)
    service_types_inferred = infer_service_types(db, only_missing=True)
    liaison_contacts_created = seed_liaison_contacts(db, only_missing=True)
    vo_csh_inferred = infer_vo_csh_renewal_dates(db, only_missing=True)

    return {
        "departments_imported": int(new_depts),
        "clients_from_contacts": int(new_clients),
        "expiry_dates_rolled": int(expiry_rolled),
        "ird_passwords_migrated": int(ird_migrated),
        "service_types_inferred": int(service_types_inferred),
        "liaison_contacts_created": int(liaison_contacts_created),
        "vo_renewals_inferred": int(vo_csh_inferred["vo"]),
        "csh_renewals_inferred": int(vo_csh_inferred["csh"]),
        "folders_linked": int(folder_result["linked"]),
        "folders_created": int(folder_result["created"]),
        "folders_failed": int(folder_result["failed"]),
        "failed_folder_names": list(folder_result.get("failed_names") or []),
    }
