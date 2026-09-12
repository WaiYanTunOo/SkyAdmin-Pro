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
    try:
        from importlib.metadata import version as _pkg_version

        return _pkg_version("skyadmin-pro")
    except Exception:
        pass
    return "0.3.3"


APP_NAME = "SkyAdmin Pro"
APP_TAGLINE = "Wai Yan Tun Oo (SKY)"
APP_VERSION = _resolve_app_version()

# Default appearance — Settings will override from SQLite.
DEFAULT_APPEARANCE_MODE = "light"  # "dark" | "light" | "system"
DEFAULT_COLOR_THEME = "blue"

# ── Re-export everything from sub-modules ────────────────────────────────

# nav
# documents
# ── Checklist / renewal data (modularized in config/checklists.py) ─────
from skyadmin_pro.config.checklists import (  # noqa: E402
    CHECKLIST_TEMPLATES,
    COMPANY_SETUP_CHECKLIST_ITEMS,
    CSH_RENEWAL_CHECKLIST_ITEMS,
    GENERAL_RENEWAL_CHECKLIST_ITEMS,
    GENERAL_RENEWAL_TEMPLATE_NAME,
    PASSPORT_RENEWAL_CHECKLIST_ITEMS,
    RENEWAL_CHECKLIST_ITEMS,
    RENEWAL_TEMPLATE_MAP,
    VAT_ADDRESS_CHECKLIST_ITEMS,
    VO_RENEWAL_CHECKLIST_ITEMS,
    WORK_PERMIT_RENEWAL_CHECKLIST_ITEMS,
    renewal_template_for,
)

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
