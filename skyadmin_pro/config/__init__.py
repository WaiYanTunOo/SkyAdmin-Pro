"""
Application constants, default settings, and UI copy.

Re-exports every public name from the sub-modules so that
``from skyadmin_pro.config import X`` continues to work unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _resolve_app_version() -> str:
    """Read version from pyproject.toml (dev + frozen bundle) with safe fallback."""
    try:
        import tomllib

        candidates: list[Path] = []
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            candidates.append(Path(sys._MEIPASS) / "pyproject.toml")
        root = Path(__file__).resolve().parents[1]
        candidates.extend([root / "pyproject.toml", Path.cwd() / "pyproject.toml"])
        for path in candidates:
            if not path.is_file():
                continue
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            version = data.get("project", {}).get("version")
            if version:
                return str(version)
    except Exception:
        pass
    return "0.3.3"


APP_NAME = "SkyAdmin Pro"
APP_TAGLINE = "Wai Yan Tun Oo (SKY)"
APP_VERSION = _resolve_app_version()

# Default appearance — Settings will override from SQLite.
DEFAULT_APPEARANCE_MODE = "dark"  # "dark" | "light" | "system"
DEFAULT_COLOR_THEME = "blue"

# ── Re-export everything from sub-modules ────────────────────────────────

# nav
# documents
from .documents import (  # noqa: E402
    FINANCIAL_DOC_CATEGORIES,
    FINANCIAL_DOC_FOLDER_MAP,
    FINANCIAL_DOC_SUBCATEGORIES,
    IMAGE_SUFFIXES,
    PDF_SUFFIX,
)

# licensing
from .licensing import (  # noqa: E402
    API_BASE_URL,
    LEGAL_DISCLAIMER_SHORT,
    LEGAL_DISCLAIMER_TEXT,
    LEGAL_LICENSE_TEXT,
    MOBILE_VIEWER_URL,
    PRICING_OVER_YEAR_TEXT,
    PRICING_TIERS,
    REVOCATION_URL,
    SETTING_DATA_SYNC_ENABLED,
    SETTING_SYNC_LAST_PULL,
    SETTING_SYNC_LAST_PUSH,
)
from .nav import (  # noqa: E402
    NAV_DASHBOARD,
    NAV_DATABASE_TASKS,
    NAV_DOCUMENT_HUB,
    NAV_ITEMS,
    NAV_OFFICE_HUB,
    NAV_SETTINGS,
    NAV_UTILITIES,
)

# office
from .office import (  # noqa: E402
    CLIENT_CREDENTIAL_TYPES,
    CONTACT_CATEGORIES,
    NOTEBOOK_ENTRY_TYPES,
    OFFICE_SYSTEM_TYPES,
    OWNER_BUSINESS_NAME,
    OWNER_EMAIL,
    OWNER_WHATSAPP_DISPLAY,
    OWNER_WHATSAPP_NUMBER,
    VAULT_CATEGORIES,
)

# pricing
from .pricing import (  # noqa: E402
    ACCOUNTING_PRICING_SERVICES,
    DEFAULT_FLAT_FEE_PRICING,
    DEFAULT_PRICING_MATRIX,
    DEFAULT_SERVICE_CHARGE_LINES,
    FLAT_FEE_TRANSACTION_RANGE,
    PAYMENT_STATUSES,
    PRICING_DEFAULT_SERVICE,
    TRANSACTION_RANGE_PRICING_SERVICES,
    default_charge_lines_for,
    is_transaction_volume_tier,
    pricing_uses_transaction_ranges,
)

# services
from .services import (  # noqa: E402
    ACCOUNTING_DOCUMENT_TYPES,
    ACCOUNTING_SERVICE_INFER_PRIORITY,
    ANNUAL_DEC31_SERVICE_MARKERS,
    CSH_DOCUMENT_TYPES,
    DOC_TYPE_ACCOUNTING,
    DOC_TYPE_COMPANY,
    DOC_TYPE_INVOICE,
    DOC_TYPE_LICENSE,
    DOC_TYPE_OTHER,
    DOC_TYPE_PASSPORT_VISA,
    DOC_TYPES_WITH_AMOUNT,
    DOC_TYPES_WITH_EXPIRY,
    DOCUMENT_TO_ACCOUNTING_SERVICE,
    DOCUMENT_TO_VO_CSH_RENEWAL,
    DOCUMENT_TYPES,
    IMPORTANT_DOC_TYPES,
    MONTHLY_TAX_TYPES,
    SERVICE_PROGRESS,
    SERVICE_TYPES,
    TAX_FILING_FIELDS,
    TAX_FILING_LABELS,
    TAX_FILING_STATUSES,
    TRANSACTION_RANGES,
    VO_CSH_DOCUMENT_TYPES,
    VO_DOCUMENT_TYPES,
)

# tasks
from .tasks import (  # noqa: E402
    COURIER_DRIVERS,
    DEFAULT_WINDOW_GEOMETRY,
    EXPIRY_ALERT_DAYS,
    EXPIRY_WATCH_TYPES,
    MIN_WINDOW_SIZE,
    NEW_CUSTOMER_QUOTATION_TASKS,
    PIPELINE_MAX_STEP,
    PIPELINE_STEPS,
    PIPELINE_TASK_CATEGORIES,
    SERVICE_TASK_CATEGORY,
    SETTING_APP_TAGLINE,
    SETTING_APPEARANCE_MODE,
    SETTING_COLOR_THEME,
    SETTING_DEPARTMENT_LIST,
    SETTING_LAST_ENCRYPTED_BACKUP,
    SETTING_ORGANIZATION_LIST,
    SETTING_SERVICE_TYPES,
    SETTING_SIDEBAR_COLLAPSED,
    SETTING_SNIPPET_OVERRIDES,
    SETTING_TABLE_COLUMNS,
    SETTING_WINDOW_GEOMETRY,
    SETTING_WORKSPACE_CUSTOM,
    SETTING_WORKSPACE_ROOT,
    TASK_CATEGORIES,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_PENDING,
    service_task_category,
)

# workspace
from .workspace import (  # noqa: E402
    CLIENT_WORKSPACE_FOLDERS,
    DEFAULT_PORTAL_URL,
    FOLDER_ARCHIVE,
    FOLDER_CLIENTS,
    FOLDER_PORTAL_BACKUP,
    FOLDER_READY,
    FOLDER_STAGING,
    FOLDER_SUPPLIERS,
    SETTING_PORTAL_URL,
)

# ── Checklist / renewal data (kept here because it spans domains) ──────

# Visa / work-permit renewal financial-document checklist (from the SOP).
RENEWAL_CHECKLIST_ITEMS: tuple[tuple[str, int], ...] = (
    ("Initiate renewal; get the document checklist from the visa agent", 90),
    ("Extract P.N.D.1 returns — 3-6 months, each with Pay-in Slip + e-Receipt", 60),
    ("Extract P.P.30 returns — 3-6 months, each with Pay-in Slip + e-Receipt", 60),
    ("Collect SSF contribution reports and receipts", 60),
    ("Latest audited financial statement", 45),
    ("Most recent P.N.D.50", 45),
    ("Print all documents", 30),
    ("Check out the corporate seal; stamp every page", 30),
    ("Director signs every page in blue ink", 30),
    ("Verify P.N.D.1 name matches passport and salary meets the minimum", 30),
    ("Prepare waterproof pack and arrange trackable courier", 25),
    ("After renewal: scan new visa stamp + work permit; update expiry dates", 0),
)

PASSPORT_RENEWAL_CHECKLIST_ITEMS: tuple[tuple[str, int], ...] = (
    ("Confirm passport expiry; check the renewal window with the embassy/agent", 90),
    ("Get the document checklist for passport renewal from the agent", 90),
    ("Prepare passport photos and application forms", 60),
    ("Collect supporting documents (company certificate, stamps, etc.)", 45),
    ("Print all documents", 30),
    ("Director signs every page in blue ink", 30),
    ("Arrange trackable courier to the agent/embassy", 25),
    ("After renewal: scan new passport pages; update expiry dates", 0),
)

COMPANY_SETUP_CHECKLIST_ITEMS: tuple[tuple[str, int], ...] = (
    ("Prepare company registration documents (MOA, DBD, etc.)", 60),
    ("Draft shareholder and director details for filing", 45),
    ("Open the corporate bank account", 30),
    ("Register for tax (VAT / PND) after incorporation", 30),
    ("Deliver signed originals to the agent", 25),
    ("After setup: scan certificates; update records", 0),
)

GENERAL_RENEWAL_CHECKLIST_ITEMS: tuple[tuple[str, int], ...] = (
    ("Confirm the renewal terms and document checklist with the agent", 45),
    ("Collect the required documents for the renewal", 30),
    ("Print all documents and arrange signatures", 21),
    ("Prepare and send the courier to the agent/office", 14),
    ("Confirm the renewal completed; scan proof and update expiry dates", 0),
)

VAT_ADDRESS_CHECKLIST_ITEMS: tuple[tuple[str, int], ...] = (
    ("Company Affidavit (issued within the last 6 months)", 30),
    ("List of Shareholders — Bor Or Jor. 5 (issued within the last 6 months)", 30),
    ("Company stamp", 30),
    ("Lease agreement with required stamp duty affixed", 21),
    ("Copy of landlord's ID card", 21),
    ("Copy of land title deed", 21),
    ("Copy of house registration showing landlord as owner", 21),
    ("Exterior photos — house number and acrylic company signboard", 14),
    ("Interior photos of the new premises", 14),
    ("Photos of surrounding areas", 14),
    ("Graphic map of new business address", 14),
)

WORK_PERMIT_RENEWAL_CHECKLIST_ITEMS: tuple[tuple[str, int], ...] = (
    ("Copy of passport", 60),
    ("Copy of current work permit", 60),
    ("Passport-size photo — white background, PNG format", 60),
    ("Company Affidavit (issued within last 6 months) + receipt", 45),
    ("List of Shareholders — Bor Or Jor 5 + receipt", 45),
    ("Medical Certificate for work permit application (700 THB via agent)", 45),
    ("Latest 3 months' PP.30 (VAT) filings", 30),
    ("PND.91 — Tax Return + Tax Payment Receipt", 30),
    ("2025 Financial Statements + Sor Bor Chor 3", 30),
    ("PND.50 — Tax Return + Tax Payment Receipt", 30),
)

VO_RENEWAL_CHECKLIST_ITEMS: tuple[tuple[str, int], ...] = (
    ("Confirm VO contract renewal terms with provider", 60),
    ("Collect updated VO agreement / invoice", 45),
    ("Process payment for VO renewal", 30),
    ("Update VO address in company records", 0),
)

CSH_RENEWAL_CHECKLIST_ITEMS: tuple[tuple[str, int], ...] = (
    ("Confirm CSH contract renewal terms with provider", 60),
    ("Collect updated CSH agreement / invoice", 45),
    ("Process payment for CSH renewal", 30),
    ("Update CSH records in company files", 0),
)

GENERAL_RENEWAL_TEMPLATE_NAME = "General Renewal"

CHECKLIST_TEMPLATES: tuple[tuple[str, tuple[tuple[str, int], ...]], ...] = (
    ("Visa Renewal", RENEWAL_CHECKLIST_ITEMS),
    ("Passport Renewal", PASSPORT_RENEWAL_CHECKLIST_ITEMS),
    ("Company Setup", COMPANY_SETUP_CHECKLIST_ITEMS),
    ("Work Permit Renewal", WORK_PERMIT_RENEWAL_CHECKLIST_ITEMS),
    ("VAT Address Update", VAT_ADDRESS_CHECKLIST_ITEMS),
    ("VO Renewal", VO_RENEWAL_CHECKLIST_ITEMS),
    ("CSH Renewal", CSH_RENEWAL_CHECKLIST_ITEMS),
    (GENERAL_RENEWAL_TEMPLATE_NAME, GENERAL_RENEWAL_CHECKLIST_ITEMS),
)

RENEWAL_TEMPLATE_MAP: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Passport Renewal", ("Passport",)),
    ("Company Setup", ("Company Setup", "Company Registration")),
    ("Work Permit Renewal", ("Work Permit Renewal",)),
    ("Visa Renewal", ("Non-B Business Visa", "Work Permit", "Visa")),
)


def renewal_template_for(document_type: str) -> str | None:
    """Return the checklist template name for a service's document type."""
    low = (document_type or "").lower()
    for template, patterns in RENEWAL_TEMPLATE_MAP:
        if any(pattern.lower() in low for pattern in patterns):
            return template
    return None
