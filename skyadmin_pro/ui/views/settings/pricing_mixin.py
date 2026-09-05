"""Settings view mixins."""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from skyadmin_pro.config import (
    PRICING_DEFAULT_SERVICE,
    SETTING_PORTAL_URL,
    pricing_uses_transaction_ranges,
)
from skyadmin_pro.services.workflow import normalize_portal_url
from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.widgets import make_modal, themed_entry


class PricingMixin:
    def _refresh_pricing_services(self) -> None:
        services = self.app.db.list_pricing_service_types()
        if not services:
            services = [PRICING_DEFAULT_SERVICE]
        self.pricing_service_menu.configure(values=services)
        current = self.pricing_service_menu.get()
        if current not in services:
            self.pricing_service_menu.set(services[0])

    def _configure_pricing_form_for_service(self, service_type: str) -> None:
        uses_ranges = pricing_uses_transaction_ranges(service_type)
        if uses_ranges:
            self.pricing_tree.tree.heading("range", text="Transaction range")
            self.pricing_range_heading.configure(text="Transaction range")
            self.pricing_range_menu.grid(row=0, column=1, sticky="ew", pady=4)
            self.pricing_charge_entry.grid_remove()
            self.pricing_add_charge_btn.grid_remove()
            self.pricing_delete_charge_btn.grid_remove()
            self.pricing_monthly_label.configure(text="Monthly fee (THB)")
            self.pricing_annual_entry.grid(row=1, column=1, sticky="ew", pady=4)
            self.pricing_headcount_entry.grid(row=2, column=1, sticky="ew", pady=4)
        else:
            self.pricing_tree.tree.heading("range", text="Charge line")
            self.pricing_range_heading.configure(text="Charge line")
            self.pricing_range_menu.grid_remove()
            self.pricing_charge_entry.grid(row=0, column=1, sticky="ew", pady=4)
            self.pricing_add_charge_btn.grid()
            self.pricing_delete_charge_btn.grid()
            self.pricing_monthly_label.configure(text="Fee (THB)")
            self.pricing_annual_entry.grid_remove()
            self.pricing_headcount_entry.grid_remove()
            self.pricing_annual_var.set("")
            self.pricing_headcount_var.set("")

    def _refresh_pricing_matrix(self) -> None:
        service_type = self.pricing_service_menu.get().strip() or PRICING_DEFAULT_SERVICE
        self._configure_pricing_form_for_service(service_type)
        rows = self.app.db.get_pricing_matrix(service_type=service_type)
        self._pricing_rows = {str(row["id"]): row for row in rows}
        tree_rows = [
            (
                row.get("transaction_range") or "",
                f"{(row.get('monthly_fee') or 0):,}",
                f"{(row.get('annual_fee') or 0):,}",
                str(row.get("sla_hours") or ""),
                str(row.get("headcount") or ""),
                row.get("required_docs") or "",
            )
            for row in rows
        ]
        self.pricing_tree.set_rows(
            tree_rows,
            iids=[str(row["id"]) for row in rows],
            empty_message="No pricing tiers for this service yet.",
        )
        if rows:
            first = str(rows[0]["id"])
            self.pricing_tree.tree.selection_set(first)
            self.pricing_tree.tree.focus(first)
            self._on_pricing_row_select(first)

    def _on_pricing_service_change(self, _choice: str) -> None:
        self._refresh_pricing_matrix()

    def _on_pricing_row_select(self, iid: str | None) -> None:
        if not iid:
            self._selected_pricing_id = None
            return
        row = self._pricing_rows.get(str(iid))
        if not row:
            self._selected_pricing_id = None
            return
        self._selected_pricing_id = int(iid)
        self._load_pricing_tier(row.get("transaction_range") or "")

    def _load_pricing_tier(self, transaction_range: str) -> None:
        service_type = self.pricing_service_menu.get().strip() or PRICING_DEFAULT_SERVICE
        self._configure_pricing_form_for_service(service_type)
        tier = self.app.db.lookup_pricing_by_range(transaction_range, service_type=service_type)
        self.pricing_range_var.set(transaction_range)
        self.pricing_monthly_var.set(str(tier.get("monthly_fee") or "") if tier else "")
        self.pricing_annual_var.set(str(tier.get("annual_fee") or "") if tier else "")
        self.pricing_sla_var.set(str(tier.get("sla_hours") or "") if tier else "")
        self.pricing_headcount_var.set(str(tier.get("headcount") or "") if tier else "")
        self.pricing_docs_var.set(str(tier.get("required_docs") or "") if tier else "")
        if tier:
            self._selected_pricing_id = int(tier["id"])

    def _reset_service_pricing(self) -> None:
        service_type = self.pricing_service_menu.get().strip() or PRICING_DEFAULT_SERVICE
        uses_ranges = pricing_uses_transaction_ranges(service_type)
        label = "transaction tiers" if uses_ranges else "charge lines"
        if not messagebox.askyesno(
            "Reset pricing",
            f"Reset all {label} for '{service_type}' to defaults?",
            parent=self.winfo_toplevel(),
        ):
            return
        self.app.db.reset_service_pricing_to_defaults(service_type)
        self.feedback.success(f"Pricing reset for {service_type}.")
        self._refresh_pricing_matrix()

    def _seed_all_service_pricing(self) -> None:
        self.app.db._seed_all_service_pricing()
        self._refresh_pricing_services()
        self._refresh_pricing_matrix()
        self.feedback.success("Pricing tiers ensured for all services.")

    def _save_pricing_tier(self) -> None:
        service_type = self.pricing_service_menu.get().strip() or PRICING_DEFAULT_SERVICE
        uses_ranges = pricing_uses_transaction_ranges(service_type)
        transaction_range = self.pricing_range_var.get().strip()
        if not transaction_range:
            label = "transaction range" if uses_ranges else "charge line"
            self.feedback.error(f"Enter a {label} first.")
            return

        def _parse_int(value: str, label: str) -> int | None:
            raw = value.strip()
            if not raw:
                return None
            try:
                return int(raw.replace(",", ""))
            except ValueError as exc:
                raise ValueError(f"{label} must be a whole number.") from exc

        try:
            fee_label = "Fee" if not uses_ranges else "Monthly fee"
            monthly = _parse_int(self.pricing_monthly_var.get(), fee_label)
            annual = _parse_int(self.pricing_annual_var.get(), "Annual fee") if uses_ranges else 0
            sla = _parse_int(self.pricing_sla_var.get(), "SLA hours")
            headcount = _parse_int(self.pricing_headcount_var.get(), "Headcount") if uses_ranges else 0
        except ValueError as exc:
            self.feedback.error(str(exc))
            return

        docs = self.pricing_docs_var.get().strip() or None
        selected_id = getattr(self, "_selected_pricing_id", None)
        tier = (
            self.app.db.get_pricing_tier(int(selected_id))
            if selected_id
            else self.app.db.lookup_pricing_by_range(transaction_range, service_type=service_type)
        )
        try:
            if tier:
                self.app.db.update_pricing_tier(
                    tier["id"],
                    transaction_range=transaction_range,
                    monthly_fee=monthly,
                    annual_fee=annual,
                    sla_hours=sla,
                    headcount=headcount,
                    required_docs=docs,
                )
            else:
                self.app.db.add_pricing_tier(
                    service_type=service_type,
                    transaction_range=transaction_range,
                    monthly_fee=monthly or 0,
                    annual_fee=annual or 0,
                    sla_hours=sla or 0,
                    headcount=headcount or 0,
                    required_docs=docs or "",
                )
        except Exception as exc:
            self.feedback.error(f"Could not save pricing: {exc}")
            return
        self.feedback.success(f"Pricing saved for {service_type}.")
        self._refresh_pricing_matrix()
        self.app.set_status(f"Pricing updated: {service_type} / {transaction_range}")

    def _add_pricing_charge_line(self) -> None:
        service_type = self.pricing_service_menu.get().strip() or PRICING_DEFAULT_SERVICE
        if pricing_uses_transaction_ranges(service_type):
            self.feedback.error("Charge lines apply only to flat-fee services.")
            return
        self._open_charge_line_dialog(service_type)

    def _open_charge_line_dialog(self, service_type: str) -> None:
        top = ctk.CTkToplevel(self.winfo_toplevel())
        top.title("New charge line")
        top.resizable(False, False)
        top.geometry("420x180")
        top.update_idletasks()
        width, height = 420, 180
        x = (self.winfo_rootx() + self.winfo_width() // 2) - width // 2
        y = (self.winfo_rooty() + self.winfo_height() // 2) - height // 2
        top.geometry(f"{width}x{height}+{x}+{y}")
        top.deiconify()
        top.lift()
        top.focus_force()
        make_modal(top)
        top.grid_columnconfigure(0, weight=1)

        body = ctk.CTkFrame(top, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew", padx=20, pady=(20, 12))
        body.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            body,
            text="Charge name (e.g. DBD fee, Registration fee)",
            anchor="w",
            text_color=TEXT_MUTED,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        name_var = ctk.StringVar()
        name_entry = themed_entry(body, textvariable=name_var)
        name_entry.grid(row=1, column=0, sticky="ew")
        name_entry.focus_set()

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.grid(row=2, column=0, sticky="e", pady=(16, 0))
        ctk.CTkButton(
            buttons, text="Cancel", width=90, fg_color="transparent", border_width=1, command=top.destroy
        ).grid(row=0, column=0, padx=(0, 8))

        def save() -> None:
            charge_name = name_var.get().strip()
            if not charge_name:
                self.feedback.error("Charge line name cannot be empty.")
                return
            if self.app.db.lookup_pricing_by_range(charge_name, service_type=service_type):
                self.feedback.error(f"Charge line '{charge_name}' already exists.")
                return
            try:
                tier_id = self.app.db.add_pricing_tier(
                    service_type=service_type,
                    transaction_range=charge_name,
                    monthly_fee=0,
                    annual_fee=0,
                    sla_hours=0,
                    headcount=0,
                    required_docs="",
                )
            except Exception as exc:
                self.feedback.error(f"Could not add charge line: {exc}")
                return
            top.destroy()
            self.feedback.success(f"Added charge line: {charge_name}")
            self._refresh_pricing_matrix()
            self.pricing_tree.tree.selection_set(str(tier_id))
            self.pricing_tree.tree.focus(str(tier_id))
            self._on_pricing_row_select(str(tier_id))

        save_btn = ctk.CTkButton(buttons, text="Add", width=90, command=save)
        save_btn.grid(row=0, column=1)
        name_entry.bind("<Return>", lambda _e: save())

    def _delete_pricing_charge_line(self) -> None:
        service_type = self.pricing_service_menu.get().strip() or PRICING_DEFAULT_SERVICE
        if pricing_uses_transaction_ranges(service_type):
            self.feedback.error("Charge lines apply only to flat-fee services.")
            return
        selected_id = getattr(self, "_selected_pricing_id", None)
        if not selected_id:
            self.feedback.error("Select a charge line to delete.")
            return
        row = self._pricing_rows.get(str(selected_id))
        if not row:
            self.feedback.error("Select a charge line to delete.")
            return
        charge_name = row.get("transaction_range") or "this charge line"
        if not messagebox.askyesno(
            "Delete charge line",
            f"Delete '{charge_name}' from {service_type}?",
            parent=self.winfo_toplevel(),
        ):
            return
        self.app.db.delete_pricing_tier(int(selected_id))
        self._selected_pricing_id = None
        self.feedback.success(f"Deleted charge line: {charge_name}")
        self._refresh_pricing_matrix()

    def _save_portal(self) -> None:
        try:
            url = normalize_portal_url(self.portal_var.get())
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.app.db.set_setting(SETTING_PORTAL_URL, url)
        self.portal_var.set(url)
        self.feedback.success("Portal URL saved.")
