from __future__ import annotations

from tkinter import messagebox

from skyadmin_pro.config import PRICING_DEFAULT_SERVICE, SETTING_PORTAL_URL, pricing_uses_transaction_ranges
from skyadmin_pro.services.workflow import normalize_portal_url


class PricingMixinMixin3:
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
        self._reconfigure_tab_scroll(self.tabs.tab("Business"))

    def _save_portal(self) -> None:
        try:
            url = normalize_portal_url(self.portal_var.get())
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.app.db.set_setting(SETTING_PORTAL_URL, url)
        self.portal_var.set(url)
        self.feedback.success("Portal URL saved.")
