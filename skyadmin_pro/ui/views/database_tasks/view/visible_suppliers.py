"""Supplier sheet visible-column helpers for Excel export."""

from __future__ import annotations

from skyadmin_pro.config import NAV_SUPPLIERS

from .visible_cols import add_visible_sheet_fields


def collect_supplier_visible(result: dict, ensure) -> None:
    view = ensure(NAV_SUPPLIERS)
    panel = getattr(view, "panel", None)
    if panel is None:
        return
    ensure_tab = getattr(panel, "_ensure_supplier_tab", None)
    if callable(ensure_tab):
        for name in ("Suppliers", "Supplier Services", "Payments (AP)"):
            try:
                ensure_tab(name)
            except Exception:
                pass
    directory = getattr(panel, "directory", None)
    add_visible_sheet_fields(
        result,
        "Suppliers",
        getattr(directory, "supplier_tree", None) or getattr(panel, "supplier_tree", None),
        {"name": "name", "company": "company_name", "contact": "contact", "notes": "notes"},
    )
    services = getattr(panel, "services", None)
    add_visible_sheet_fields(
        result,
        "Supplier Services",
        getattr(services, "supplier_svc_tree", None) or getattr(panel, "supplier_svc_tree", None),
        {
            "company": "company_name",
            "service": "service_type",
            "expiry": "expiry_date",
            "notes": "notes",
        },
    )
    payments = getattr(panel, "payments", None)
    add_visible_sheet_fields(
        result,
        "Supplier Payments",
        getattr(payments, "pay_tree", None) or getattr(panel, "pay_tree", None),
        {
            "supplier": "supplier_name",
            "client": "client_name",
            "amount": "amount",
            "due": "due_date",
            "paid": "paid",
            "paid_date": "paid_date",
            "notes": "notes",
        },
    )
