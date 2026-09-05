"""Document Hub constants: file suffixes, financial doc categories, and folder mapping."""

from __future__ import annotations

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
PDF_SUFFIX = ".pdf"

FINANCIAL_DOC_CATEGORIES: tuple[str, ...] = (
    "Tax Invoice",
    "Quotation",
    "Pay Slip",
    "Bank Transfer",
    "Bank Slip",
    "Tax Receipt",
    "General Expense",
)

FINANCIAL_DOC_SUBCATEGORIES: tuple[str, ...] = (
    "Client",
    "Supplier",
    "Company",
    "Tax Authority",
)

FINANCIAL_DOC_FOLDER_MAP: dict[str, str] = {
    "Tax Invoice": "Invoices",
    "Quotation": "Quotations",
    "Pay Slip": "Pay_Slips",
    "Bank Transfer": "Bank_Transfers",
    "Bank Slip": "Bank_Slips",
    "Tax Receipt": "Tax_Receipts",
    "General Expense": "General_Expenses",
}
