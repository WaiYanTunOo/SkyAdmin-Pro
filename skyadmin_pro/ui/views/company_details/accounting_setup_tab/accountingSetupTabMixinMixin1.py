from __future__ import annotations

from tkinter import messagebox

from skyadmin_pro.services.tax_ids_rollout import apply_pricing_tier, infer_service_types, list_accounting_setup_rows
from skyadmin_pro.ui.views.company_details.constants import SUBTAB_GENERAL, SUBTAB_TAX_IDS


class AccountingSetupTabMixinMixin1:
    def _infer_selected_service_type(self) -> None:
        row = self._selected_accounting_setup_row()
        if not row:
            self.feedback.error("Select an accounting client first.")
            return
        suggested = (row.get("suggested_service_type") or "").strip()
        if not suggested:
            self.feedback.error("No service type can be inferred from this client's documents.")
            return
        current_type = (row.get("service_type") or "").strip()
        if (
            current_type
            and current_type != suggested
            and not messagebox.askyesno(
                "Overwrite service type",
                f"Replace '{row.get('service_type')}' with inferred '{suggested}'?",
                parent=self.winfo_toplevel(),
            )
        ):
            return
        self.app.db.update_client_fields(int(row["id"]), service_type=suggested)
        self.feedback.success(f"Service type set to {suggested}.")
        self.refresh_accounting_setup()
        if self._selected_client_id() == int(row["id"]):
            tab = self._current_subtab()
            if tab == SUBTAB_TAX_IDS:
                self._refresh_after_mutation(SUBTAB_TAX_IDS)
            elif tab == SUBTAB_GENERAL:
                self._refresh_after_mutation(SUBTAB_GENERAL)

    def _infer_all_service_types(self) -> None:
        pending = sum(
            1
            for row in list_accounting_setup_rows(self.app.db)
            if not (row.get("service_type") or "").strip() and (row.get("suggested_service_type") or "").strip()
        )
        if pending == 0:
            self.feedback.info("No clients need service-type inference.")
            return
        if not messagebox.askyesno(
            "Infer service types",
            f"Infer service type from documents for {pending} client(s) that do not have one yet?",
            parent=self.winfo_toplevel(),
        ):
            return
        updated = infer_service_types(self.app.db, only_missing=True)
        self.feedback.success(f"Inferred service type for {updated} client(s).")
        self.refresh_accounting_setup()

    def _apply_selected_pricing_tier(self) -> None:
        row = self._selected_accounting_setup_row()
        if not row:
            self.feedback.error("Select an accounting client first.")
            return
        client_id = int(row["id"])
        if not (row.get("service_type") or "").strip():
            self.feedback.error("Set service type first (use Infer service type).")
            return
        if not (row.get("num_transactions") or "").strip():
            self.feedback.error("Set transaction volume in Tax IDs before applying pricing.")
            return
        if apply_pricing_tier(self.app.db, client_id):
            self.feedback.success("Pricing tier applied from matrix.")
            self.refresh_accounting_setup()
            if self._selected_client_id() == client_id:
                tab = self._current_subtab()
                if tab == SUBTAB_TAX_IDS:
                    self._refresh_after_mutation(SUBTAB_TAX_IDS)
        else:
            self.feedback.error("No matching pricing tier — check Settings → Pricing matrix.")
