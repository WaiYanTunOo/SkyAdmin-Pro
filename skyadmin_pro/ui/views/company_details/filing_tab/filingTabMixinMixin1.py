from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import TAX_FILING_FIELDS, TAX_FILING_LABELS, TAX_FILING_STATUSES
from skyadmin_pro.ui.views.company_details.constants import SUBTAB_FILING
from skyadmin_pro.ui.widgets import make_modal


class FilingTabMixinMixin1:
    def _edit_filing_status(self, field: str) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        label = TAX_FILING_LABELS.get(field, field)
        current = self.filing_vars[field].get()
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Edit {label}")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        make_modal(dialog)
        ctk.CTkLabel(dialog, text=f"Status for {label}:").grid(row=0, column=0, padx=16, pady=(12, 4), sticky="w")
        status_var = ctk.StringVar(value=current)
        ctk.CTkOptionMenu(
            dialog,
            values=list(TAX_FILING_STATUSES),
            variable=status_var,
            width=200,
        ).grid(row=0, column=1, padx=(0, 16), pady=(12, 4), sticky="ew")

        def _confirm() -> None:
            new_val = status_var.get()
            old_val = self.filing_vars[field].get()
            if new_val != old_val:
                self.app.db.log_tax_change(client_id, field, old_val, new_val)
                self.app.db.update_client_fields(client_id, **{field: new_val})
                if new_val in ("Pending", "On-Going"):
                    client = self.app.db.get_client(client_id)
                    client_name = (client or {}).get("name") or "client"
                    self.app.db.add_task(
                        title=f"Tax filing: {label} — {client_name}",
                        client_id=client_id,
                        category="General",
                        description=f"Status changed from {old_val} to {new_val}.",
                    )
            dialog.destroy()
            self.feedback.success(f"{label} updated to {new_val}.")
            self._refresh_after_mutation(SUBTAB_FILING)

        ctk.CTkButton(dialog, text="Save", width=100, command=_confirm).grid(
            row=1, column=0, columnspan=2, pady=(12, 16)
        )

    def _reset_filing_status(self, field: str) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        label = TAX_FILING_LABELS.get(field, field)
        old_val = self.filing_vars[field].get()
        if old_val == "Not Applicable":
            return
        self.app.db.log_tax_change(client_id, field, old_val, "Not Applicable")
        self.app.db.update_client_fields(client_id, **{field: "Not Applicable"})
        self.feedback.success(f"{label} reset to N/A.")
        self._refresh_after_mutation(SUBTAB_FILING)

    def _reset_all_filing_statuses(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        updates = {}
        for field in TAX_FILING_FIELDS:
            old_val = self.filing_vars[field].get()
            if old_val != "Not Applicable":
                self.app.db.log_tax_change(client_id, field, old_val, "Not Applicable")
                updates[field] = "Not Applicable"
        if updates:
            self.app.db.update_client_fields(client_id, **updates)
            self.feedback.success(f"{len(updates)} filing status(es) reset to N/A.")
        else:
            self.feedback.info("All filing statuses already N/A.")
        self._refresh_after_mutation(SUBTAB_FILING)
