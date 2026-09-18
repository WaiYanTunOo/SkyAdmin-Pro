from __future__ import annotations

from tkinter import messagebox

from skyadmin_pro.config import PRICING_DEFAULT_SERVICE, pricing_uses_transaction_ranges


class PricingMixinMixin1:
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
        self._reconfigure_tab_scroll(self.tabs.tab("Business"))

    def _add_pricing_charge_line(self) -> None:
        service_type = self.pricing_service_menu.get().strip() or PRICING_DEFAULT_SERVICE
        if pricing_uses_transaction_ranges(service_type):
            self.feedback.error("Charge lines apply only to flat-fee services.")
            return
        self._open_charge_line_dialog(service_type)
