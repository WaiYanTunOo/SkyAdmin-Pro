"""Pricing matrix, charge-line defaults, and transaction-range helpers."""

from __future__ import annotations

from .services import TRANSACTION_RANGES  # noqa: F401

PRICING_DEFAULT_SERVICE = "General"

FLAT_FEE_TRANSACTION_RANGE = "Flat fee"

ACCOUNTING_PRICING_SERVICES: tuple[str, ...] = (
    "Yearly Accounting",
    "Monthly Accounting",
    "Monthly Tax Filing",
    "Mid-Year Tax Filing",
    "Annual Audit",
)

TRANSACTION_RANGE_PRICING_SERVICES: frozenset[str] = frozenset({PRICING_DEFAULT_SERVICE, *ACCOUNTING_PRICING_SERVICES})

DEFAULT_SERVICE_CHARGE_LINES: dict[str, tuple[tuple[str, int, int, int, int, str], ...]] = {
    "Company Setup Basic Package": (
        ("Package base fee", 0, 0, 0, 0, ""),
        ("DBD fee", 0, 0, 0, 0, ""),
        ("Registration fee", 0, 0, 0, 0, ""),
        ("VAT service charge", 0, 0, 0, 0, ""),
    ),
}

DEFAULT_PRICING_MATRIX: tuple[tuple[str, int, int, int, int, str], ...] = (
    ("Non-Operation Business (No Transaction)", 6000, 72000, 8, 1, "Bank Statement, Service Invoices"),
    (
        "1 to 50 Transactions",
        12000,
        144000,
        8,
        1,
        "Bank Statement, Service Invoices, Purchase Invoice/BL, Tax Invoice/Receipt, Sale Invoices/DN",
    ),
    (
        "51 to 100 Transactions",
        18000,
        216000,
        16,
        2,
        "Bank Statement, Service Invoices, Purchase Invoice/BL, Tax Invoice/Receipt, Sale Invoices/DN",
    ),
    (
        "101 to 200 Transactions",
        24000,
        288000,
        24,
        2,
        "Bank Statement, Service Invoices, Purchase Invoice/BL, Tax Invoice/Receipt, Sale Invoices/DN, Warehouse Receipt",
    ),
    (
        "200+ Transactions",
        30000,
        360000,
        24,
        3,
        "Bank Statement, Service Invoices, Purchase Invoice/BL, Tax Invoice/Receipt, Sale Invoices/DN, Warehouse Receipt, Transport Documents",
    ),
)

DEFAULT_FLAT_FEE_PRICING: tuple[tuple[str, int, int, int, int, str], ...] = (("Service fee", 0, 0, 0, 0, ""),)

PAYMENT_STATUSES: tuple[str, ...] = ("Paid", "Pending", "N/A")


def pricing_uses_transaction_ranges(service_type: str) -> bool:
    """Accounting-style services use the 5-tier transaction volume grid."""
    return (service_type or "").strip() in TRANSACTION_RANGE_PRICING_SERVICES


def default_charge_lines_for(
    service_type: str,
) -> tuple[tuple[str, int, int, int, int, str], ...]:
    """Named charge rows for a flat-fee service (multiple fees allowed)."""
    clean = (service_type or "").strip()
    if clean in DEFAULT_SERVICE_CHARGE_LINES:
        return DEFAULT_SERVICE_CHARGE_LINES[clean]
    low = clean.casefold()
    if "company setup" in low:
        return DEFAULT_SERVICE_CHARGE_LINES["Company Setup Basic Package"]
    if "medical certificate" in low:
        return (("Medical certificate fee", 0, 0, 0, 0, ""),)
    return (("Service fee", 0, 0, 0, 0, ""),)


def is_transaction_volume_tier(label: str) -> bool:
    return (label or "").strip() in TRANSACTION_RANGES
