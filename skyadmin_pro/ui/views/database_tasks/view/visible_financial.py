"""Financial Docs trees → Excel visible columns."""

from __future__ import annotations

from skyadmin_pro.config import NAV_DATABASE_TASKS, NAV_DOCUMENT_HUB

from .visible_cols import add_visible_sheet_fields


def collect_financial_visible(result: dict, ensure) -> None:
    """Prefer Document Hub; fall back to Company Details financial docs."""
    hub = ensure(NAV_DOCUMENT_HUB)
    ensure_hub = getattr(hub, "_ensure_panel", None)
    if callable(ensure_hub):
        try:
            ensure_hub("Financial Docs")
        except Exception:
            pass
    fin = getattr(hub, "financial", None)
    add_visible_sheet_fields(
        result,
        "Financial Docs",
        getattr(fin, "tree", None) if fin is not None else None,
        {
            "client": "client_name",
            "date": "doc_date",
            "category": "category",
            "filename": "file_name",
            "amount": "amount",
            "description": "description",
        },
    )
    if "Financial Docs" in result:
        return

    companies = ensure(NAV_DATABASE_TASKS)
    ensure_panel = getattr(companies, "_ensure_panel", None)
    if callable(ensure_panel):
        try:
            from ._const_4 import TAB_COMPANY

            ensure_panel(TAB_COMPANY)
        except Exception:
            pass
    company = getattr(companies, "company_panel", None)
    add_visible_sheet_fields(
        result,
        "Financial Docs",
        getattr(company, "fin_doc_tree", None),
        {
            "date": "doc_date",
            "category": "category",
            "subcategory": "subcategory",
            "file": "file_name",
            "amount": "amount",
            "desc": "description",
        },
    )
