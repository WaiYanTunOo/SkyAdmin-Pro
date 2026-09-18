from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.services.file_ops import parse_flexible_date


class SupplierServicesTabMixin0:
    """Supplier services form and list (embedded in SuppliersPanel tabview)."""

    def __init__(self, master: ctk.CTkFrame, host: SuppliersPanel) -> None:
        svc_btns, svc_card = self._SupplierServicesTab__init__p1(host, master)
        self._SupplierServicesTab__init__p2(svc_btns, svc_card)

    def refresh(self) -> None:
        self.supplier_svc_tree.apply_theme()
        self._refresh_supplier_services()

    def _selected_supplier_id(self) -> int | None:
        return self.host.directory.selected_supplier_id

    def _refresh_supplier_services(self) -> None:
        supplier_id = self._selected_supplier_id()
        if supplier_id is None:
            self.supplier_svc_tree.set_rows([], empty_message="Select a supplier in the Directory tab first.")
            return
        services = self.app.db.list_supplier_services(supplier_id)
        self.supplier_svc_tree.set_rows(
            [
                (
                    s["company_name"],
                    s["service_type"],
                    s.get("expiry_date") or "—",
                    s.get("notes") or "",
                )
                for s in services
            ],
            iids=[str(s["id"]) for s in services],
            empty_message="No services for this supplier yet.",
        )

    def _add_supplier_service(self) -> None:
        supplier_id = self._selected_supplier_id()
        if supplier_id is None:
            self.feedback.error("Select a supplier first (Suppliers tab).")
            return
        company = self.svc_company.get().strip()
        service = self.svc_service.get().strip()
        if not company or not service:
            self.feedback.error("Enter company and service name.")
            return
        expiry = parse_flexible_date(self.svc_expiry_var.get().strip())
        if self.svc_expiry_var.get().strip() and expiry is None:
            self.feedback.error("Enter a valid expiry date (YYYY-MM-DD or DD/MM/YYYY).")
            return
        notes = self.svc_notes.get().strip() or None
        try:
            if self._editing_svc_id:
                self.app.db.update_supplier_service(
                    self._editing_svc_id,
                    company_name=company,
                    service_type=service,
                    expiry_date=expiry,
                    notes=notes,
                )
                self.feedback.success("Supplier service updated.")
            else:
                self.app.db.add_supplier_service(
                    supplier_id=supplier_id,
                    company_name=company,
                    service_type=service,
                    expiry_date=expiry,
                    notes=notes,
                )
                self.feedback.success("Supplier service added.")
        except Exception as exc:
            self.feedback.error(f"Could not save supplier service: {exc}")
            return
        self._clear_svc_form()
        self._refresh_supplier_services()

    def _clear_svc_form(self) -> None:
        self._editing_svc_id = None
        self.svc_company.delete(0, "end")
        self.svc_service.delete(0, "end")
        self.svc_expiry_var.set("")
        self.svc_notes.delete(0, "end")
