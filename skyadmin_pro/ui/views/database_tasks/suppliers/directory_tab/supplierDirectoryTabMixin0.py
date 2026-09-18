from __future__ import annotations

import customtkinter as ctk


class SupplierDirectoryTabMixin0:
    """Supplier directory form and list (embedded in SuppliersPanel tabview)."""

    def __init__(self, master: ctk.CTkFrame, host: SuppliersPanel) -> None:
        card = self._SupplierDirectoryTab__init__p1(host, master)
        self._SupplierDirectoryTab__init__p2(card)

    def refresh(self) -> None:
        """Reload the supplier tree (non-blocking; DB off the Tk thread)."""
        from skyadmin_pro.ui.async_ui import run_background

        self.supplier_tree.apply_theme()
        if not hasattr(self, "_refresh_seq"):
            self._refresh_seq = 0
        self._refresh_seq += 1
        seq = self._refresh_seq
        db = self.app.db
        host = self.host

        def work():
            return db.list_suppliers()

        def on_success(suppliers) -> None:
            if seq != self._refresh_seq:
                return
            try:
                exists = host.winfo_exists()
            except Exception:
                return
            if not exists:
                return
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
                empty_message="No suppliers yet — add one above.",
            )

        def on_error(msg: str) -> None:
            if seq != self._refresh_seq:
                return
            try:
                self.feedback.error(f"Suppliers failed to load: {msg}")
            except Exception:
                pass

        run_background(host, work=work, on_success=on_success, on_error=on_error)

    def _on_supplier_select(self, iid: str | None) -> None:
        if iid is None:
            self.selected_supplier_id = None
            if self.on_supplier_selected:
                self.on_supplier_selected(None)
            return
        try:
            supplier = self.app.db.get_supplier(int(iid))
        except Exception:
            supplier = None
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
