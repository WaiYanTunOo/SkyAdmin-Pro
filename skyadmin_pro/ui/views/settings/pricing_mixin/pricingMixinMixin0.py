from __future__ import annotations

from skyadmin_pro.config import PRICING_DEFAULT_SERVICE, pricing_uses_transaction_ranges


class PricingMixinMixin0:
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
