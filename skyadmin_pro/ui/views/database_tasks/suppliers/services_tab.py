"""Supplier services tab — per-supplier service and expiry tracking."""

from __future__ import annotations

from tkinter import messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

from skyadmin_pro.services.file_ops import parse_flexible_date
from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import DatePickerField, themed_entry

if TYPE_CHECKING:
    from skyadmin_pro.ui.views.database_tasks.suppliers.panel import SuppliersPanel


class SupplierServicesTab:
    """Supplier services form and list (embedded in SuppliersPanel tabview)."""

    def __init__(self, master: ctk.CTkFrame, host: SuppliersPanel) -> None:
        self.host = host
        self.app = host.app
        self.feedback = host.feedback
        self._editing_svc_id: int | None = None

        scroll = ctk.CTkScrollableFrame(master, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        svc_card = ctk.CTkFrame(scroll, corner_radius=CARD_RADIUS)
        svc_card.grid(row=0, column=0, sticky="ew")
        svc_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            svc_card,
            text="Supplier services — tracked per supplier",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))

        hint = ctk.CTkLabel(
            svc_card,
            text="Select a supplier in the Suppliers tab first, then add services here.",
            text_color=("gray40", "gray60"),
            anchor="w",
        )
        hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        svc_form = ctk.CTkFrame(svc_card, fg_color="transparent")
        svc_form.grid(row=2, column=0, sticky="ew", padx=16)
        svc_form.grid_columnconfigure(1, weight=1)
        svc_form.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(svc_form, text="Company").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.svc_company = themed_entry(svc_form, placeholder_text="Company name")
        self.svc_company.grid(row=0, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(svc_form, text="Service").grid(row=0, column=2, sticky="w", padx=(12, 8), pady=4)
        self.svc_service = themed_entry(svc_form, placeholder_text="e.g. Non-VAT Address")
        self.svc_service.grid(row=0, column=3, sticky="ew", pady=4)
        ctk.CTkLabel(svc_form, text="Expiry date").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.svc_expiry_var = ctk.StringVar()
        DatePickerField(svc_form, var=self.svc_expiry_var).grid(row=1, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(svc_form, text="Notes").grid(row=1, column=2, sticky="w", padx=(12, 8), pady=4)
        self.svc_notes = themed_entry(svc_form, placeholder_text="Optional")
        self.svc_notes.grid(row=1, column=3, sticky="ew", pady=4)

        svc_btns = ctk.CTkFrame(svc_card, fg_color="transparent")
        svc_btns.grid(row=3, column=0, sticky="ew", padx=16, pady=(4, 4))
        ctk.CTkButton(svc_btns, text="Add service", width=110, command=self._add_supplier_service).pack(side="left")
        ctk.CTkButton(
            svc_btns,
            text="Edit",
            width=70,
            command=self._edit_supplier_service,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            svc_btns,
            text="Delete",
            width=70,
            fg_color="transparent",
            border_width=1,
            command=self._delete_supplier_service,
        ).pack(side="left", padx=(8, 0))

        self.supplier_svc_tree = ThemedTreeview(
            svc_card,
            columns=(
                ("company", "Company", 200),
                ("service", "Service", 200),
                ("expiry", "Expiry date", 120),
                ("notes", "Notes", 200),
            ),
            showheight=10,
        )
        self.supplier_svc_tree.grid(row=4, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def refresh(self) -> None:
        self.supplier_svc_tree.apply_theme()
        self._refresh_supplier_services()

    def _selected_supplier_id(self) -> int | None:
        return self.host.directory.selected_supplier_id

    def _refresh_supplier_services(self) -> None:
        supplier_id = self._selected_supplier_id()
        if supplier_id is None:
            self.supplier_svc_tree.set_rows([])
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
        self._clear_svc_form()
        self._refresh_supplier_services()

    def _clear_svc_form(self) -> None:
        self._editing_svc_id = None
        self.svc_company.delete(0, "end")
        self.svc_service.delete(0, "end")
        self.svc_expiry_var.set("")
        self.svc_notes.delete(0, "end")

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
        self.svc_company.delete(0, "end")
        self.svc_company.insert(0, svc["company_name"])
        self.svc_service.delete(0, "end")
        self.svc_service.insert(0, svc["service_type"])
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
        self.app.db.delete_supplier_service(int(iid))
        self.feedback.success("Supplier service deleted.")
        self._refresh_supplier_services()
