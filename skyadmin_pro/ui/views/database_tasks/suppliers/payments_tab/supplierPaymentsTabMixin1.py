from __future__ import annotations

from skyadmin_pro.services.file_ops import format_thousands, parse_flexible_date, sanitize_amount
from skyadmin_pro.ui.combo_utils import fill_combo


class SupplierPaymentsTabMixin1:
    def _save_payment(self) -> None:
        supplier_name = self.pay_supplier.get().strip()
        if not supplier_name:
            self.feedback.error("Select or type a supplier name.")
            return
        try:
            supplier_id = self.app.db.get_or_create_supplier(supplier_name)
        except Exception as exc:
            self.feedback.error(f"Could not resolve supplier: {exc}")
            return
        client_id: int | None = None
        client_name = self.pay_client.get().strip()
        if client_name:
            try:
                client_id = self.app.db.client_id_by_name(client_name)
            except Exception:
                client_id = None
            if client_id is None:
                self.feedback.error(f"Client '{client_name}' does not exist — add the client first.")
                return
        raw_amount = self.pay_amount.get().strip()
        pay_date = parse_flexible_date(self.pay_date_var.get().strip())
        if self.pay_date_var.get().strip() and pay_date is None:
            self.feedback.error("Enter a valid payment date (YYYY-MM-DD or DD/MM/YYYY).")
            return
        due_date = parse_flexible_date(self.pay_due_var.get().strip())
        if self.pay_due_var.get().strip() and due_date is None:
            self.feedback.error("Enter a valid due date (YYYY-MM-DD or DD/MM/YYYY).")
            return
        fields = dict(
            supplier_id=supplier_id,
            client_id=client_id,
            amount=sanitize_amount(raw_amount) if raw_amount else None,
            due_date=due_date,
            paid_date=pay_date,
            notes=self.pay_notes.get().strip() or None,
        )
        try:
            if self._editing_payment_id:
                self.app.db.update_supplier_payment(self._editing_payment_id, **fields)
                self.feedback.success("Supplier payment updated.")
            else:
                self.app.db.add_supplier_payment(**fields)
                self.feedback.success("Supplier payment recorded.")
        except Exception as exc:
            self.feedback.error(f"Could not save payment: {exc}")
            return
        self._new_payment()
        self.host.refresh()

    def _edit_payment(self) -> None:
        iid = self.pay_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a payment to edit.")
            return
        payment = self.app.db.get_supplier_payment(int(iid))
        if payment is None:
            self.feedback.error("Payment record not found.")
            return
        self._editing_payment_id = int(iid)
        self.pay_save_btn.configure(text="Save payment")
        fill_combo(
            self.pay_supplier,
            [s["name"] for s in self.app.db.list_suppliers()],
            payment.get("supplier_name") or "",
        )
        fill_combo(
            self.pay_client,
            self.app.db.list_client_names(),
            payment.get("client_name") or "",
        )
        self.pay_amount.delete(0, "end")
        if payment.get("amount"):
            self.pay_amount.insert(0, format_thousands(payment["amount"]))
        self.pay_due_var.set(payment.get("due_date") or "")
        self.pay_date_var.set(payment.get("paid_date") or "")
        self.pay_notes.delete(0, "end")
        if payment.get("notes"):
            self.pay_notes.insert(0, payment["notes"])

    def _new_payment(self) -> None:
        self._editing_payment_id = None
        self.pay_save_btn.configure(text="Add payment")
        self.pay_tree.tree.selection_remove(*self.pay_tree.tree.selection())
        self.pay_amount.delete(0, "end")
        self.pay_due_var.set("")
        self.pay_date_var.set("")
        self.pay_notes.delete(0, "end")
