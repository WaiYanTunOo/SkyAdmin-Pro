"""Workspace folder constants and portal settings."""

from __future__ import annotations

FOLDER_STAGING = "00_Staging_Area"
FOLDER_READY = "02_Ready_to_Upload"
FOLDER_ARCHIVE = "Z_Archive_Backup"
FOLDER_CLIENTS = "Clients"
FOLDER_SUPPLIERS = "Suppliers"
FOLDER_PORTAL_BACKUP = "Portal_Backups"

CLIENT_WORKSPACE_FOLDERS: tuple[str, ...] = (
    "01_Company_Setup",
    "02_Accounting",
    "03_Visa",
    "04_Financial_Docs",
)

DEFAULT_PORTAL_URL = "https://example.com/portal"

# SQLite setting keys related to workspace.
SETTING_PORTAL_URL = "portal_url"
