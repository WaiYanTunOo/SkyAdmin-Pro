from __future__ import annotations

from datetime import date
from tkinter import messagebox

import customtkinter as ctk

from skyadmin_pro.services.file_ops import parse_flexible_date
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.widgets import DatePickerField, make_modal


class SupplierPaymentsTabMixin2:
    def _mark_paid(self) -> None:
        iid = self.pay_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a payment first.")
            return
        try:
            payment = self.app.db.get_supplier_payment(int(iid))
        except Exception:
            payment = None
        if payment is None:
            self.feedback.error("Payment record not found.")
            return
        top = ctk.CTkToplevel(self.host.winfo_toplevel())
        top.title("Mark as paid")
        top.resizable(False, False)
        top.geometry("380x230")
        top.update_idletasks()
        width, height = 380, 230
        x = (self.host.winfo_rootx() + self.host.winfo_width() // 2) - width // 2
        y = (self.host.winfo_rooty() + self.host.winfo_height() // 2) - height // 2
        top.geometry(f"{width}x{height}+{x}+{y}")
        top.deiconify()
        top.lift()
        top.focus_force()
        make_modal(top)

        ctk.CTkLabel(
            top,
            text=payment.get("supplier_name") or "Supplier",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 2))
        ctk.CTkLabel(
            top,
            text="Pick the date this payment was actually made.",
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=20)

        ctk.CTkLabel(top, text="Payment date", anchor="w").grid(row=2, column=0, sticky="w", padx=20, pady=(10, 2))
        date_var = ctk.StringVar(value=payment.get("paid_date") or date.today().isoformat())
        DatePickerField(top, var=date_var).grid(row=3, column=0, sticky="ew", padx=20)

        def _do() -> None:
            value = date_var.get().strip()
            parsed = parse_flexible_date(value)
            if not parsed:
                self.feedback.error("Enter a valid payment date.")
                return
            try:
                self.app.db.set_supplier_payment_paid(int(iid), True, paid_date=parsed)
            except Exception as exc:
                self.feedback.error(f"Could not mark as paid: {exc}")
                return
            top.destroy()
            self.feedback.success("Payment marked as paid.")
            self.host.refresh()

        ctk.CTkButton(top, text="Confirm paid", command=_do).grid(row=4, column=0, sticky="ew", padx=20, pady=(12, 18))

    def _delete_payment(self) -> None:
        iid = self.pay_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a payment first.")
            return
        if not messagebox.askyesno(
            "Delete payment",
            "Delete this payment record?",
            parent=self.host.winfo_toplevel(),
        ):
            return
        try:
            self.app.db.delete_supplier_payment(int(iid))
        except Exception as exc:
            self.feedback.error(f"Could not delete payment: {exc}")
            return
        self.feedback.success("Payment deleted.")
        self.host.refresh()
