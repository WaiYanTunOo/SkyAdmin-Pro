from __future__ import annotations

from skyadmin_pro.config import TAX_FILING_FIELDS
from skyadmin_pro.ui.views.company_details.constants import SUBTAB_FILING


class FilingTabMixinMixin1:
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
