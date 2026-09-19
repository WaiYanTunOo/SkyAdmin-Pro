"""Sidebar navigation keys and item list."""

from __future__ import annotations

NAV_DASHBOARD = "dashboard"
NAV_DOCUMENT_HUB = "document_hub"
NAV_DATABASE_TASKS = "database_tasks"
NAV_TASKS = "tasks"
NAV_COURIER = "courier"
NAV_TAX_STATUS = "tax_status"
NAV_PIPELINE = "pipeline"
NAV_SUPPLIERS = "suppliers"
NAV_ACCOUNTING = "accounting_setup"
NAV_UTILITIES = "utilities"
NAV_OFFICE_HUB = "office_hub"
NAV_SETTINGS = "settings"

# Synthetic keys for group rows (not real views — never passed to show_view)
NAV_GROUP_DAILY = "group_daily"
NAV_GROUP_FINANCE = "group_finance"
NAV_GROUP_OFFICE = "group_office"

# Flat list kept for backward compatibility — all importers still work.
NAV_ITEMS: tuple[tuple[str, str], ...] = (
    (NAV_DASHBOARD, "Dashboard"),
    (NAV_TASKS, "Tasks"),
    (NAV_DATABASE_TASKS, "Companies"),
    (NAV_SUPPLIERS, "Suppliers & AP"),
    (NAV_TAX_STATUS, "Monthly Service Close"),
    (NAV_ACCOUNTING, "Accounting Setup"),
    (NAV_PIPELINE, "Service Pipeline"),
    (NAV_COURIER, "Courier Tracker"),
    (NAV_DOCUMENT_HUB, "Document Hub"),
    (NAV_OFFICE_HUB, "Office Hub"),
    (NAV_UTILITIES, "Utilities"),
    (NAV_SETTINGS, "Settings"),
)

# Grouped sidebar structure.
# Each entry: (key, label, children).
# Standalone pages have an empty children tuple.
# Group rows (group_*) are never passed to show_view — they expand/collapse only.
NAV_GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (NAV_DASHBOARD, "Dashboard", ()),
    (NAV_GROUP_DAILY, "Daily Work", (NAV_TASKS, NAV_PIPELINE, NAV_COURIER)),
    (NAV_DATABASE_TASKS, "Companies", ()),
    (NAV_GROUP_FINANCE, "Finance", (NAV_SUPPLIERS, NAV_TAX_STATUS, NAV_ACCOUNTING)),
    (NAV_GROUP_OFFICE, "Office", (NAV_DOCUMENT_HUB, NAV_OFFICE_HUB, NAV_UTILITIES)),
    (NAV_SETTINGS, "Settings", ()),
)

# Map from child key → parent group key (for auto-expand in show_view)
NAV_CHILD_TO_GROUP: dict[str, str] = {
    child: group_key for group_key, _label, children in NAV_GROUPS for child in children
}
