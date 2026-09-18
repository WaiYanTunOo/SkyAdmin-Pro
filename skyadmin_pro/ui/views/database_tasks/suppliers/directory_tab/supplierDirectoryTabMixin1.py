from __future__ import annotations

from tkinter import messagebox


class SupplierDirectoryTabMixin1:
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
        except Exception as exc:
            self.feedback.error(f"Could not save supplier: {exc}")
            return
        self.feedback.success("Supplier saved.")
        self._new_supplier()
        self.host.refresh_after_directory_change()

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
        try:
            self.app.db.delete_supplier(int(iid))
        except Exception as exc:
            self.feedback.error(f"Could not delete supplier: {exc}")
            return
        self.feedback.success("Supplier deleted (payments removed too).")
        self._new_supplier()
        self.host.refresh_after_directory_change()
