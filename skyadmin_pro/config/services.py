"""Service types, document type constants, tax filing, and VO/CSH mappings."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Document type constants
# ---------------------------------------------------------------------------
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
    "Company Certificate",
    "Affidavits",
    "BOJ Document",
    "Financial Statements",
    "Tax Returns",
    "Payments",
    DOC_TYPE_OTHER,
)

IMPORTANT_DOC_TYPES: tuple[str, ...] = (
    "Company Certificate",
    "Affidavits",
    "BOJ Document",
    "Financial Statements",
    "Tax Returns",
    "Payments",
    "Contract",
    "Passport/Visa",
    "License",
    "Company Setup",
    "Accounting",
    "Other",
)

SERVICE_PROGRESS: tuple[str, ...] = ("Not started", "Ongoing", "Completed")

DOC_TYPES_WITH_EXPIRY = frozenset({DOC_TYPE_PASSPORT_VISA, DOC_TYPE_LICENSE})
DOC_TYPES_WITH_AMOUNT = frozenset({DOC_TYPE_INVOICE})

# ---------------------------------------------------------------------------
# Service types
# ---------------------------------------------------------------------------
SERVICE_TYPES: tuple[str, ...] = (
    "Passport",
    "Non-B Business Visa",
    "Work Permit",
    "Virtual Office Rental",
    "VAT Registered Office Rental",
    "CSH (Company Thai Shareholder) Rental",
    "Company Bank Statement Request Service",
    "Financial Statement and BOJ 5.5 Filing Service",
    "Company Mid Year Accounting and Tax Submission (PND 51) Service",
    "Company Annual Accounting Service",
    "Company Monthly Accounting Service",
    "Company Annual Auditing Service",
    "Company Dissolution Service",
    "Monthly Tax Filing Service",
    "Work Permit Service",
)

MONTHLY_TAX_TYPES: tuple[str, ...] = (
    "Monthly Tax Filing Service",
    "Company Monthly Accounting Service",
)

# ---------------------------------------------------------------------------
# VO / CSH document types
# ---------------------------------------------------------------------------
VO_DOCUMENT_TYPES: tuple[str, ...] = (
    "Virtual Office Rental",
    "VAT Registered Office Rental",
)
CSH_DOCUMENT_TYPES: tuple[str, ...] = ("CSH (Company Thai Shareholder) Rental",)
VO_CSH_DOCUMENT_TYPES: tuple[str, ...] = VO_DOCUMENT_TYPES + CSH_DOCUMENT_TYPES

DOCUMENT_TO_VO_CSH_RENEWAL: dict[str, str] = {
    "Virtual Office Rental": "vo",
    "VAT Registered Office Rental": "vo",
    "CSH (Company Thai Shareholder) Rental": "csh",
}

# ---------------------------------------------------------------------------
# Accounting document types
# ---------------------------------------------------------------------------
ACCOUNTING_DOCUMENT_TYPES: tuple[str, ...] = (
    "Company Annual Accounting Service",
    "Company Monthly Accounting Service",
    "Company Mid Year Accounting and Tax Submission (PND 51) Service",
    "Company Annual Auditing Service",
    "Monthly Tax Filing Service",
    "Financial Statement and BOJ 5.5 Filing Service",
)

DOCUMENT_TO_ACCOUNTING_SERVICE: dict[str, str] = {
    "Company Annual Accounting Service": "Yearly Accounting",
    "Company Monthly Accounting Service": "Monthly Accounting",
    "Company Mid Year Accounting and Tax Submission (PND 51) Service": "Mid-Year Tax Filing",
    "Monthly Tax Filing Service": "Monthly Tax Filing",
    "Company Annual Auditing Service": "Annual Audit",
    "Financial Statement and BOJ 5.5 Filing Service": "Yearly Accounting",
}

ACCOUNTING_SERVICE_INFER_PRIORITY: tuple[str, ...] = (
    "Monthly Accounting",
    "Monthly Tax Filing",
    "Yearly Accounting",
    "Mid-Year Tax Filing",
    "Annual Audit",
)

# ---------------------------------------------------------------------------
# Tax filing
# ---------------------------------------------------------------------------
TAX_FILING_STATUSES: tuple[str, ...] = (
    "Complete",
    "Pending",
    "On-Going",
    "Not Applicable",
)

TAX_FILING_FIELDS: tuple[str, ...] = (
    "fs_status",
    "pnd53_status",
    "pp30_status",
    "pnd51_status",
    "pnd50_status",
    "audit_status",
)

TAX_FILING_LABELS: dict[str, str] = {
    "fs_status": "Financial Statement",
    "pnd53_status": "PND53",
    "pp30_status": "PP30",
    "pnd51_status": "PND51",
    "pnd50_status": "PND50",
    "audit_status": "Audit",
}

# ---------------------------------------------------------------------------
# Transaction ranges
# ---------------------------------------------------------------------------
TRANSACTION_RANGES: tuple[str, ...] = (
    "Non-Operation Business (No Transaction)",
    "1 to 50 Transactions",
    "51 to 100 Transactions",
    "101 to 200 Transactions",
    "200+ Transactions",
)

# ---------------------------------------------------------------------------
# Annual service markers
# ---------------------------------------------------------------------------
ANNUAL_DEC31_SERVICE_MARKERS: tuple[str, ...] = (
    "Company Annual Accounting Service",
    "Company Annual Auditing Service",
)
