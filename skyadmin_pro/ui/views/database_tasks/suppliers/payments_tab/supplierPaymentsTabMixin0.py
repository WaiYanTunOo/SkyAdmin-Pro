from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.services.file_ops import format_thousands
from skyadmin_pro.ui.combo_utils import fill_combo


class SupplierPaymentsTabMixin0:
    """Supplier payments form and list (embedded in SuppliersPanel tabview)."""

    def __init__(self, master: ctk.CTkFrame, host: SuppliersPanel) -> None:
        pay_card = self._SupplierPaymentsTab__init__p1(host, master)
        self._SupplierPaymentsTab__init__p2(pay_card)

    def _show_columns_menu(self) -> None:
        try:
            x = self.columns_btn.winfo_rootx()
            y = self.columns_btn.winfo_rooty() + self.columns_btn.winfo_height()
        except Exception:
            return
        self.pay_tree.show_column_menu(x, y)

    def refresh(self, suppliers: list[dict] | None = None) -> None:
        from skyadmin_pro.ui.async_ui import run_background

        self.pay_tree.apply_theme()
        try:
            cur_supplier = self.pay_supplier.get()
        except Exception:
            cur_supplier = ""
        try:
            cur_client = self.pay_client.get()
        except Exception:
            cur_client = ""
        preset = suppliers
        if not hasattr(self, "_refresh_seq"):
            self._refresh_seq = 0
        self._refresh_seq += 1
        seq = self._refresh_seq
        db = self.app.db
        host = self.host

        def work():
            sups = preset if preset is not None else db.list_suppliers()
            return {
                "suppliers": sups,
                "names": db.list_client_names(),
                "payments": db.list_supplier_payments(),
                "cur_supplier": cur_supplier,
                "cur_client": cur_client,
            }

        def on_success(payload) -> None:
            if seq != self._refresh_seq:
                return
            try:
                exists = host.winfo_exists()
            except Exception:
                return
            if not exists:
                return
            fill_combo(self.pay_supplier, [s["name"] for s in payload["suppliers"]], payload["cur_supplier"])
            fill_combo(self.pay_client, payload["names"], payload["cur_client"])
            rows: list[tuple] = []
            iids: list[str] = []
            tags: list[list[str]] = []
            for payment in payload["payments"]:
                rows.append(
                    (
                        payment.get("supplier_name") or "?",
                        payment.get("client_name") or "—",
                        format_thousands(payment.get("amount")) if payment.get("amount") else "—",
                        payment.get("due_date") or "—",
                        "Yes" if payment.get("paid") else "No",
                        payment.get("paid_date") or "—",
                        payment.get("notes") or "—",
                    )
                )
                iids.append(str(payment["id"]))
                tags.append(["completed"] if payment.get("paid") else [])
            self.pay_tree.set_rows(rows, iids=iids, tags=tags, empty_message="No supplier payments recorded.")

        def on_error(msg: str) -> None:
            if seq != self._refresh_seq:
                return
            try:
                self.feedback.error(f"Payments failed to load: {msg}")
            except Exception:
                pass

        run_background(host, work=work, on_success=on_success, on_error=on_error)

    def _format_pay_amount(self) -> None:
        value = format_thousands(self.pay_amount.get())
        self.pay_amount.delete(0, "end")
        self.pay_amount.insert(0, value)
