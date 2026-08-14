"""Application constants, default settings, and UI copy."""

from __future__ import annotations

APP_NAME = "SkyAdmin Pro"
APP_TAGLINE = "Burmese to clients · krub / 🙏 to suppliers"
APP_VERSION = "0.1.0"

# Default appearance — Settings will override from SQLite.
DEFAULT_APPEARANCE_MODE = "dark"  # "dark" | "light" | "system"
DEFAULT_COLOR_THEME = "blue"

# Sidebar navigation keys (must match view registry).
NAV_DASHBOARD = "dashboard"
NAV_DOCUMENT_HUB = "document_hub"
NAV_DATABASE_TASKS = "database_tasks"
NAV_UTILITIES = "utilities"
NAV_SETTINGS = "settings"

NAV_ITEMS: tuple[tuple[str, str], ...] = (
    (NAV_DASHBOARD, "Dashboard"),
    (NAV_DOCUMENT_HUB, "Document Hub"),
    (NAV_DATABASE_TASKS, "Database & Tasks"),
    (NAV_UTILITIES, "Utilities"),
    (NAV_SETTINGS, "Settings"),
)

# Working-folder names (created under the workspace root).
FOLDER_STAGING = "00_Staging_Area"
FOLDER_READY = "02_Ready_to_Upload"
FOLDER_ARCHIVE = "Z_Archive_Backup"
FOLDER_CLIENTS = "Clients"

DEFAULT_PORTAL_URL = "https://example.com/portal"

# Expiry alert window used by the dashboard widget (Module 2).
EXPIRY_ALERT_DAYS = 45

# SQLite setting keys.
SETTING_APPEARANCE_MODE = "appearance_mode"
SETTING_COLOR_THEME = "color_theme"
SETTING_WORKSPACE_ROOT = "workspace_root"
SETTING_PORTAL_URL = "portal_url"
SETTING_WINDOW_GEOMETRY = "window_geometry"

DEFAULT_WINDOW_GEOMETRY = "1280x800"
MIN_WINDOW_SIZE = (1100, 700)

# Document Hub — Smart Renamer
DOC_TYPE_PASSPORT_VISA = "Passport/Visa"
DOC_TYPE_INVOICE = "Invoice"
DOC_TYPE_LICENSE = "License"
DOC_TYPE_COMPANY = "Company Setup"
DOC_TYPE_ACCOUNTING = "Accounting"
DOC_TYPE_OTHER = "Other"

DOCUMENT_TYPES: tuple[str, ...] = (
    DOC_TYPE_PASSPORT_VISA,
    DOC_TYPE_INVOICE,
    DOC_TYPE_LICENSE,
    DOC_TYPE_COMPANY,
    DOC_TYPE_ACCOUNTING,
    DOC_TYPE_OTHER,
)

DOC_TYPES_WITH_EXPIRY = frozenset(
    {DOC_TYPE_PASSPORT_VISA, DOC_TYPE_LICENSE}
)
DOC_TYPES_WITH_AMOUNT = frozenset({DOC_TYPE_INVOICE})

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
PDF_SUFFIX = ".pdf"

# Database & Tasks
TASK_STATUS_PENDING = "pending"
TASK_STATUS_COMPLETED = "completed"
TASK_CATEGORIES: tuple[str, ...] = (
    "Visa",
    "Accounting",
    "Company Setup",
    "Courier",
    "Supplier",
    "General",
)
COURIER_DRIVERS: tuple[str, ...] = (
    "Grab",
    "Lalamove",
    "Kerry",
    "Thailand Post",
    "Other",
)
EXPIRY_WATCH_TYPES = frozenset({DOC_TYPE_PASSPORT_VISA, DOC_TYPE_LICENSE})

# 1-Click Client Onboarding folders under Clients/[Client Name]/
CLIENT_WORKSPACE_FOLDERS: tuple[str, ...] = (
    "01_Company_Setup",
    "02_Accounting",
    "03_Visa",
)
