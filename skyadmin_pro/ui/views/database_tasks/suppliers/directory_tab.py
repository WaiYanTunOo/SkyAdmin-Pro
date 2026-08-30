"""Supplier directory tab — CRUD for supplier records."""

from __future__ import annotations

from tkinter import messagebox
from typing import TYPE_CHECKING, Callable

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import themed_entry

if TYPE_CHECKING:
    from skyadmin_pro.ui.views.database_tasks.suppliers.panel import SuppliersPanel


class SupplierDirectoryTab:
    """Supplier directory form and list (embedded in SuppliersPanel tabview)."""

    def __init__(self, master: ctk.CTkFrame, host: SuppliersPanel) -> None:
        self.host = host
        self.app = host.app
        self.feedback = host.feedback
        self.selected_supplier_id: int | None = None
        self.on_supplier_selected: Callable[[int | None], None] | None = None

        scroll = ctk.CTkScrollableFrame(master, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(scroll, corner_radius=CARD_RADIUS)
        card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text="Supplier directory",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew", padx=16)
        form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(form, text="Name").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.sup_name = themed_entry(form, placeholder_text="Required")
        self.sup_name.grid(row=0, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(form, text="Company").grid(row=0, column=2, sticky="w", padx=(12, 8), pady=4)
        self.sup_company = themed_entry(form)
        self.sup_company.grid(row=0, column=3, sticky="ew", pady=4)
        ctk.CTkLabel(form, text="Contact").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.sup_contact = themed_entry(form)
        self.sup_contact.grid(row=1, column=1, columnspan=3, sticky="ew", pady=4)
        ctk.CTkLabel(form, text="Notes").grid(row=2, column=0, sticky="nw", padx=(0, 8), pady=4)
        self.sup_notes = ctk.CTkTextbox(form, height=100)
        self.sup_notes.grid(row=2, column=1, columnspan=3, sticky="ew", pady=4)

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        ctk.CTkButton(btns, text="Save", width=100, command=self._save_supplier).pack(side="left")
        ctk.CTkButton(
            btns,
            text="New",
            width=70,
            fg_color="transparent",
            border_width=1,
            command=self._new_supplier,
        ).pack(side="left", padx=(8, 0))

        self.supplier_tree = ThemedTreeview(
            card,
            columns=(
                ("name", "Name", 160),
                ("company", "Company", 140),
                ("contact", "Contact", 150),
                ("notes", "Notes", 260),
            ),
            on_select=self._on_supplier_select,
            showheight=8,
        )
        self.supplier_tree.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 8))
        ctk.CTkButton(
            card,
            text="Delete selected",
            fg_color="transparent",
            border_width=1,
            command=self._delete_supplier,
        ).grid(row=4, column=0, sticky="w", padx=16, pady=(0, 14))

    def refresh(self) -> list[dict]:
        """Reload the supplier tree. Returns the supplier rows for sibling tabs."""
        self.supplier_tree.apply_theme()
        suppliers = self.app.db.list_suppliers()
        self.supplier_tree.set_rows(
            [
                (
                    s["name"],
                    s.get("company_name") or "",
                    s.get("contact") or "",
                    (s.get("notes") or "")[:80],
                )
                for s in suppliers
            ],
            iids=[str(s["id"]) for s in suppliers],
        )
        return suppliers

    def _on_supplier_select(self, iid: str | None) -> None:
        if iid is None:
            self.selected_supplier_id = None
            if self.on_supplier_selected:
                self.on_supplier_selected(None)
            return
        supplier = self.app.db.get_supplier(int(iid))
        if supplier is None:
            self.selected_supplier_id = None
            if self.on_supplier_selected:
                self.on_supplier_selected(None)
            return
        self.selected_supplier_id = int(supplier["id"])
        for entry, value in (
            (self.sup_name, supplier["name"]),
            (self.sup_company, supplier.get("company_name") or ""),
            (self.sup_contact, supplier.get("contact") or ""),
        ):
            entry.delete(0, "end")
            entry.insert(0, value)
        self.sup_notes.delete("1.0", "end")
        self.sup_notes.insert("1.0", supplier.get("notes") or "")
        if self.on_supplier_selected:
            self.on_supplier_selected(self.selected_supplier_id)

    def _save_supplier(self) -> None:
        name = self.sup_name.get().strip()
        if not name:
            self.feedback.error("Enter a supplier name.")
            return
        notes = self.sup_notes.get("1.0", "end-1c").strip()
        try:
            if self.selected_supplier_id:
                self.app.db.update_supplier(
                    self.selected_supplier_id,
                    name=name,
                    company_name=self.sup_company.get(),
                    contact=self.sup_contact.get(),
                    notes=notes,
                )
            else:
                self.app.db.add_supplier(
                    name=name,
                    company_name=self.sup_company.get(),
                    contact=self.sup_contact.get(),
                    notes=notes,
                )
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success("Supplier saved.")
        self._new_supplier()
        self.host.refresh()

    def _new_supplier(self) -> None:
        self.selected_supplier_id = None
        self.supplier_tree.tree.selection_remove(*self.supplier_tree.tree.selection())
        for entry in (self.sup_name, self.sup_company, self.sup_contact):
            entry.delete(0, "end")
        self.sup_notes.delete("1.0", "end")
        if self.on_supplier_selected:
            self.on_supplier_selected(None)

    def _delete_supplier(self) -> None:
        iid = self.supplier_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a supplier first.")
            return
        if not messagebox.askyesno(
            "Delete supplier",
            "Delete this supplier?\n\nAll of their payment records will be removed too. This cannot be undone.",
            parent=self.host.winfo_toplevel(),
        ):
            return
        self.app.db.delete_supplier(int(iid))
        self.feedback.success("Supplier deleted (payments removed too).")
        self._new_supplier()
        self.host.refresh()
