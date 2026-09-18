from __future__ import annotations

SYNC_EXCLUDED_COLUMNS: dict[str, frozenset[str]] = {
    "client_groups": frozenset({"id"}),
    "clients": frozenset({"ird_password", "id", "group_id"}),
    "tasks": frozenset({"id"}),
    "office_contacts": frozenset({"id"}),
    "notebook_entries": frozenset({"id"}),
}
