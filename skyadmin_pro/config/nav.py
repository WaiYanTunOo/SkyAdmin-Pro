"""Sidebar navigation keys and item list."""

from __future__ import annotations

NAV_DASHBOARD = "dashboard"
NAV_DOCUMENT_HUB = "document_hub"
NAV_DATABASE_TASKS = "database_tasks"
NAV_UTILITIES = "utilities"
NAV_OFFICE_HUB = "office_hub"
NAV_SETTINGS = "settings"

NAV_ITEMS: tuple[tuple[str, str], ...] = (
    (NAV_DASHBOARD, "Dashboard"),
    (NAV_DOCUMENT_HUB, "Document Hub"),
    (NAV_DATABASE_TASKS, "Database & Tasks"),
    (NAV_OFFICE_HUB, "Office Hub"),
    (NAV_UTILITIES, "Utilities"),
    (NAV_SETTINGS, "Settings"),
)
