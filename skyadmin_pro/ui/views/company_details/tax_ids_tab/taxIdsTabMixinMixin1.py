from __future__ import annotations

from skyadmin_pro.services.file_ops import parse_flexible_date
from skyadmin_pro.ui.views.company_details.constants import SUBTAB_TAX_IDS


class TaxIdsTabMixinMixin1:
    def _on_txn_volume_change(self, choice: str) -> None:
        tier = self.app.db.lookup_pricing_by_range(
            choice,
            service_type=self.acct_service_type.get().strip() or None,
        )
        if not tier:
            return
        fee = tier.get("monthly_fee")
        sla = tier.get("sla_hours")
        hc = tier.get("headcount")
        fee_txt = f"{fee:,} THB/mo" if fee is not None else "not set"
        sla_txt = f"{sla}h" if sla is not None else "not set"
        hc_txt = str(hc) if hc is not None else "not set"
        current_fee = self.service_fee_var.get().strip()
        current_sla = self.sla_var.get().strip()
        current_hc = self.headcount_var.get().strip()
        # Only auto-fill if fields are empty or match a previous tier value
        if current_fee and current_sla and current_hc:
            import tkinter.messagebox as mb

            if not mb.askyesno(
                "Auto-fill pricing",
                f"Overwrite current values with pricing for '{choice}'?\n\n"
                f"Fee: {fee_txt} | SLA: {sla_txt} | HC: {hc_txt}",
                parent=self.winfo_toplevel(),
            ):
                return
        if fee is None and sla is None and hc is None:
            self.feedback.error(f"No pricing configured for '{choice}' — set it in Settings → Pricing matrix.")
            return
        if fee is not None:
            self.service_fee_var.set(str(fee))
        if sla is not None:
            self.sla_var.set(str(sla))
        if hc is not None:
            self.headcount_var.set(str(hc))

    def _save_tax_ids(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        vat_date_raw = self.vat_reg_date_var.get().strip()
        vat_date = None
        if vat_date_raw:
            vat_date = parse_flexible_date(vat_date_raw)
            if not vat_date:
                self.feedback.error("VAT registration date is not a valid date.")
                return
        try:
            self.app.db.update_client_fields(
                client_id,
                tax_id=self.tax_id_var.get().strip(),
                vat_registered=1 if self.vat_registered_var.get() else 0,
                vat_registered_date=vat_date,
                service_type=self.acct_service_type.get() or None,
                num_transactions=self.acct_txn_volume.get() or None,
                service_fee=self.service_fee_var.get().strip() or None,
                payment_status=self.acct_payment_status.get() or None,
                sla=self.sla_var.get().strip() or None,
                headcount=int(self.headcount_var.get().strip()) if self.headcount_var.get().strip().isdigit() else None,
            )
        except Exception as exc:
            self.feedback.error(f"Could not save tax IDs: {exc}")
            return
        self.feedback.success("Tax IDs & service info saved.")
        self._refresh_after_mutation(SUBTAB_TAX_IDS)
