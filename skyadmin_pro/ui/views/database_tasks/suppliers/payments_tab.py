"""Supplier payments (AP) tab — accounts payable tracking."""

from __future__ import annotations

from datetime import date
from tkinter import messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

from skyadmin_pro.services.file_ops import format_thousands, parse_flexible_date, sanitize_amount
from skyadmin_pro.ui.combo_utils import fill_combo
from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import DatePickerField, make_modal, themed_entry, themed_scrollable_frame

if TYPE_CHECKING:
    from skyadmin_pro.ui.views.database_tasks.suppliers.panel import SuppliersPanel


class SupplierPaymentsTab:
    """Supplier payments form and list (embedded in SuppliersPanel tabview)."""

    def __init__(self, master: ctk.CTkFrame, host: SuppliersPanel) -> None:
        self.host = host
        self.app = host.app
        self.feedback = host.feedback
        self._editing_payment_id: int | None = None

        scroll = themed_scrollable_frame(master)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        pay_card = ctk.CTkFrame(scroll, corner_radius=CARD_RADIUS)
        pay_card.grid(row=0, column=0, sticky="ew")
        pay_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            pay_card,
            text="Supplier payments (AP)",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        pay_form = ctk.CTkFrame(pay_card, fg_color="transparent")
        pay_form.grid(row=1, column=0, sticky="ew", padx=16)
        pay_form.grid_columnconfigure(1, weight=1)
        pay_form.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(pay_form, text="Supplier").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.pay_supplier = ctk.CTkComboBox(pay_form, values=[""])
        self.pay_supplier.grid(row=0, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(pay_form, text="Client").grid(row=0, column=2, sticky="w", padx=(12, 8), pady=4)
        self.pay_client = ctk.CTkComboBox(pay_form, values=[""])
        self.pay_client.grid(row=0, column=3, sticky="ew", pady=4)
        ctk.CTkLabel(pay_form, text="Amount (THB)").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.pay_amount = themed_entry(pay_form, placeholder_text="e.g. 15000")
        self.pay_amount.bind("<FocusOut>", lambda _e: self._format_pay_amount())
        self.pay_amount.grid(row=1, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(pay_form, text="Due date").grid(row=1, column=2, sticky="w", padx=(12, 8), pady=4)
        self.pay_due_var = ctk.StringVar()
        DatePickerField(pay_form, var=self.pay_due_var).grid(row=1, column=3, sticky="ew", pady=4)
        ctk.CTkLabel(pay_form, text="Payment date").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        self.pay_date_var = ctk.StringVar()
        DatePickerField(pay_form, var=self.pay_date_var).grid(row=2, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(pay_form, text="Notes").grid(row=2, column=2, sticky="w", padx=(12, 8), pady=4)
        self.pay_notes = themed_entry(pay_form)
        self.pay_notes.grid(row=2, column=3, sticky="ew", pady=4)
        pay_form_btns = ctk.CTkFrame(pay_card, fg_color="transparent")
        pay_form_btns.grid(row=2, column=0, sticky="w", padx=16, pady=(8, 4))
        self.pay_save_btn = ctk.CTkButton(pay_form_btns, text="Add payment", width=120, command=self._save_payment)
        self.pay_save_btn.pack(side="left")
        ctk.CTkButton(pay_form_btns, text="Edit", width=70, command=self._edit_payment).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            pay_form_btns,
            text="New",
            width=70,
            fg_color="transparent",
            border_width=1,
            command=self._new_payment,
        ).pack(side="left", padx=(8, 0))

        self.pay_tree = ThemedTreeview(
            pay_card,
            columns=(
                ("supplier", "Supplier", 150),
                ("client", "Client", 130),
                ("amount", "Amount", 90),
                ("due", "Due date", 90),
                ("paid", "Paid", 60),
                ("paid_date", "Paid date", 90),
                ("notes", "Notes", 160),
            ),
            showheight=10,
        )
        self.pay_tree.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 8))
        pay_btns = ctk.CTkFrame(pay_card, fg_color="transparent")
        pay_btns.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 14))
        ctk.CTkButton(pay_btns, text="Mark paid", width=110, command=self._mark_paid).pack(side="left")
        ctk.CTkButton(
            pay_btns,
            text="Delete",
            width=90,
            fg_color="transparent",
            border_width=1,
            command=self._delete_payment,
        ).pack(side="left", padx=(8, 0))

    def refresh(self, suppliers: list[dict] | None = None) -> None:
        self.pay_tree.apply_theme()
        if suppliers is None:
            suppliers = self.app.db.list_suppliers()
        fill_combo(self.pay_supplier, [s["name"] for s in suppliers], self.pay_supplier.get())
        fill_combo(self.pay_client, self.app.db.list_client_names(), self.pay_client.get())

        payments = self.app.db.list_supplier_payments()
        rows: list[tuple] = []
        iids: list[str] = []
        tags: list[list[str]] = []
        for payment in payments:
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
        self.pay_tree.set_rows(rows, iids=iids, tags=tags)

    def _format_pay_amount(self) -> None:
        value = format_thousands(self.pay_amount.get())
        self.pay_amount.delete(0, "end")
        self.pay_amount.insert(0, value)

    def _save_payment(self) -> None:
        supplier_name = self.pay_supplier.get().strip()
        if not supplier_name:
            self.feedback.error("Select or type a supplier name.")
            return
        supplier_id = self.app.db.get_or_create_supplier(supplier_name)
        client_id: int | None = None
        client_name = self.pay_client.get().strip()
        if client_name:
            client_id = self.app.db.client_id_by_name(client_name)
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
        if self._editing_payment_id:
            self.app.db.update_supplier_payment(self._editing_payment_id, **fields)
            self.feedback.success("Supplier payment updated.")
        else:
            self.app.db.add_supplier_payment(**fields)
            self.feedback.success("Supplier payment recorded.")
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

    def _mark_paid(self) -> None:
        iid = self.pay_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a payment first.")
            return
        payment = self.app.db.get_supplier_payment(int(iid))
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
            self.app.db.set_supplier_payment_paid(int(iid), True, paid_date=parsed)
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
        self.app.db.delete_supplier_payment(int(iid))
        self.feedback.success("Payment deleted.")
        self.host.refresh()
