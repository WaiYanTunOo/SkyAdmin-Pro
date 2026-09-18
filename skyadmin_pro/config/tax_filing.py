"""Tax filing status fields: monthly PND cycle vs annual returns."""

from __future__ import annotations

TAX_FILING_STATUSES: tuple[str, ...] = (
    "Complete",
    "Pending",
    "On-Going",
    "Not Applicable",
)

# Monthly cycle flips only these (PND 1, 3, 53, PP30).
MONTHLY_FILING_FIELDS: tuple[str, ...] = (
    "pnd1_status",
    "pnd3_status",
    "pnd53_status",
    "pp30_status",
)

# Annual / mid-year returns (PND 90, 91, 50, 51) plus FS and Audit.
ANNUAL_FILING_FIELDS: tuple[str, ...] = (
    "pnd90_status",
    "pnd91_status",
    "pnd50_status",
    "pnd51_status",
    "fs_status",
    "audit_status",
)

TAX_FILING_FIELDS: tuple[str, ...] = MONTHLY_FILING_FIELDS + ANNUAL_FILING_FIELDS

TAX_FILING_LABELS: dict[str, str] = {
    "pnd1_status": "PND1",
    "pnd3_status": "PND3",
    "pnd53_status": "PND53",
    "pp30_status": "PP30",
    "pnd90_status": "PND90",
    "pnd91_status": "PND91",
    "pnd50_status": "PND50",
    "pnd51_status": "PND51",
    "fs_status": "Financial Statement",
    "audit_status": "Audit",
}

FILING_FIELD_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Monthly", MONTHLY_FILING_FIELDS),
    ("Annual", ANNUAL_FILING_FIELDS),
)
