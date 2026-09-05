"""Task statuses, categories, pipeline, and all SQLite setting-key constants."""

from __future__ import annotations

# Re-use the doc-type constants that tasks depend on.
from .services import DOC_TYPE_LICENSE, DOC_TYPE_PASSPORT_VISA  # noqa: F401

# ---------------------------------------------------------------------------
# Task statuses
# ---------------------------------------------------------------------------
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

EXPIRY_ALERT_DAYS = 45

# ---------------------------------------------------------------------------
# 9-Step Client-to-Supplier pipeline
# ---------------------------------------------------------------------------
PIPELINE_STEPS: tuple[str, ...] = (
    "1. Client appoints service",
    "2. Client invoice sent",
    "3. Client paid",
    "4. Requirements checked with supplier",
    "5. Docs requested from client",
    "6. Docs sent to supplier",
    "7. Supplier paid",
    "8. Processing & follow-up",
    "9. Completed",
)
PIPELINE_MAX_STEP: int = len(PIPELINE_STEPS)

PIPELINE_TASK_CATEGORIES: dict[int, str] = {
    1: "Company Setup",
    2: "Accounting",
    3: "Accounting",
    4: "Supplier",
    5: "General",
    6: "Supplier",
    7: "Supplier",
    8: "General",
    9: "General",
}

SERVICE_TASK_CATEGORY: dict[str, str] = {
    "Passport": "Visa",
    "Non-B Business Visa": "Visa",
    "Work Permit": "Visa",
    "Work Permit Service": "Visa",
    "Virtual Office Rental": "General",
    "VAT Registered Office Rental": "General",
    "CSH (Company Thai Shareholder) Rental": "General",
    "Company Bank Statement Request Service": "General",
    "Company Dissolution Service": "Company Setup",
    "Company Annual Accounting Service": "Accounting",
    "Company Monthly Accounting Service": "Accounting",
    "Company Annual Auditing Service": "Accounting",
    "Company Mid Year Accounting and Tax Submission (PND 51) Service": "Accounting",
    "Financial Statement and BOJ 5.5 Filing Service": "Accounting",
    "Monthly Tax Filing Service": "Accounting",
}


def service_task_category(document_type: str) -> str:
    """Map a service type to a task category (defaults to General)."""
    return SERVICE_TASK_CATEGORY.get((document_type or "").strip(), "General")


# ---------------------------------------------------------------------------
# New-customer quotation tasks
# ---------------------------------------------------------------------------
NEW_CUSTOMER_QUOTATION_TASKS: tuple[tuple[str, int, str], ...] = (
    ("Send quotation to {client}", 0, "General"),
    ("Follow up quotation — {client}", 2, "General"),
    ("Quotation decision — {client}", 5, "General"),
)

# ---------------------------------------------------------------------------
# All SQLite setting-key constants
# ---------------------------------------------------------------------------
SETTING_APPEARANCE_MODE = "appearance_mode"
SETTING_COLOR_THEME = "color_theme"
SETTING_WORKSPACE_ROOT = "workspace_root"
SETTING_WORKSPACE_CUSTOM = "workspace_custom"
SETTING_PORTAL_URL = "portal_url"
SETTING_WINDOW_GEOMETRY = "window_geometry"
SETTING_SIDEBAR_COLLAPSED = "sidebar_collapsed"
SETTING_SNIPPET_OVERRIDES = "snippet_overrides"
SETTING_SERVICE_TYPES = "service_types"
SETTING_ORGANIZATION_LIST = "organization_list"
SETTING_DEPARTMENT_LIST = "department_list"
SETTING_APP_TAGLINE = "app_tagline"
SETTING_LAST_ENCRYPTED_BACKUP = "last_encrypted_backup"

DEFAULT_WINDOW_GEOMETRY = "1280x800"
MIN_WINDOW_SIZE = (1100, 700)
