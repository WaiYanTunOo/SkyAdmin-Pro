"""Company Details panel — per-company services, tax, VO/CSH, and documents."""

from __future__ import annotations

from skyadmin_pro.config import (
    TRANSACTION_RANGES,
)

# Sub-tab names — single source of truth for the tab bar, lazy loader,
# refresh dispatcher, and cross-module callers (database_tasks/view.py).


class CompanyDetailsPanelMixin8:
    def _refresh_tax_ids_subtab(self, client_id: int | None, client: dict | None) -> None:
        if client_id is None:
            self.tax_id_var.set("")
            self._load_client_credentials_display(None)
            self.vat_registered_var.set(False)
            self.vat_reg_date_var.set("")
            self.acct_service_type.set("")
            self.acct_txn_volume.set("")
            self.service_fee_var.set("")
            self.acct_payment_status.set("")
            self.sla_var.set("")
            self.headcount_var.set("")
            return

        self.tax_id_var.set((client or {}).get("tax_id") or "")
        self._load_client_credentials_display(client_id)
        self.vat_registered_var.set(bool((client or {}).get("vat_registered")))
        self.vat_reg_date_var.set((client or {}).get("vat_registered_date") or "")
        self.acct_service_type.set((client or {}).get("service_type") or "")
        acct_txn = (client or {}).get("num_transactions") or ""
        if acct_txn in TRANSACTION_RANGES:
            self.acct_txn_volume.set(acct_txn)
        else:
            self.acct_txn_volume.set(TRANSACTION_RANGES[0] if TRANSACTION_RANGES else "")
        self.service_fee_var.set((client or {}).get("service_fee") or "")
        self.acct_payment_status.set((client or {}).get("payment_status") or "N/A")
        self.sla_var.set((client or {}).get("sla") or "")
        hc = (client or {}).get("headcount")
        self.headcount_var.set(str(hc) if hc is not None else "")
