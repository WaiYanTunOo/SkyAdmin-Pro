from __future__ import annotations

from tkinter import messagebox

from skyadmin_pro.ui.combo_utils import fill_combo


class SupplierServicesTabMixin1:
    def _refresh_svc_combos(self, company: str = "", service: str = "") -> None:
        companies = [""] + list(self.app.db.list_client_names() or [])
        services = [""] + list(self.app.db.list_service_types() or [])
        if company and company not in companies:
            companies.append(company)
        if service and service not in services:
            services.append(service)
        fill_combo(self.svc_company, companies, company)
        fill_combo(self.svc_service, services, service)

    def _edit_supplier_service(self) -> None:
        supplier_id = self._selected_supplier_id()
        iid = self.supplier_svc_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a service to edit.")
            return
        if supplier_id is None:
            self.feedback.error("Select a supplier first (Suppliers tab).")
            return
        services = self.app.db.list_supplier_services(supplier_id)
        svc = next((s for s in services if str(s["id"]) == iid), None)
        if svc is None:
            return
        self._editing_svc_id = int(iid)
        self._refresh_svc_combos(svc.get("company_name") or "", svc.get("service_type") or "")
        self.svc_expiry_var.set(svc.get("expiry_date") or "")
        self.svc_notes.delete(0, "end")
        if svc.get("notes"):
            self.svc_notes.insert(0, svc["notes"])

    def _delete_supplier_service(self) -> None:
        iid = self.supplier_svc_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a service first.")
            return
        if not messagebox.askyesno(
            "Delete supplier service",
            "Delete this supplier service record?",
            parent=self.host.winfo_toplevel(),
        ):
            return
        try:
            self.app.db.delete_supplier_service(int(iid))
        except Exception as exc:
            self.feedback.error(f"Could not delete supplier service: {exc}")
            return
        self.feedback.success("Supplier service deleted.")
        self._refresh_supplier_services()
