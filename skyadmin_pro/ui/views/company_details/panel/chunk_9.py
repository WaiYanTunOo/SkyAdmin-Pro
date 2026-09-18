"""Company Details panel — per-company services, tax, VO/CSH, and documents."""

from __future__ import annotations

from skyadmin_pro.config import (
    TAX_FILING_FIELDS,
    TAX_FILING_STATUSES,
)

# Sub-tab names — single source of truth for the tab bar, lazy loader,
# refresh dispatcher, and cross-module callers (database_tasks/view.py).


class CompanyDetailsPanelMixin9:
    def _refresh_filing_subtab(self, client_id: int | None, client: dict | None) -> None:
        if client_id is None:
            for field in TAX_FILING_FIELDS:
                if field in self.filing_vars:
                    self.filing_vars[field].set("Not Applicable")
            for _key, lbl in self.filing_summary_labels.items():
                lbl.configure(text="0")
            self.filing_last_changed_label.configure(text="")
            return

        counts = {"complete": 0, "ongoing": 0, "pending": 0, "na": 0}
        self._filing_suspend_save = True
        try:
            for field in TAX_FILING_FIELDS:
                val = (client or {}).get(field) or "Not Applicable"
                if val not in TAX_FILING_STATUSES:
                    val = "Not Applicable"
                self.filing_vars[field].set(val)
                if val == "Complete":
                    counts["complete"] += 1
                elif val == "On-Going":
                    counts["ongoing"] += 1
                elif val == "Pending":
                    counts["pending"] += 1
                else:
                    counts["na"] += 1
        finally:
            self._filing_suspend_save = False
        for key, lbl in self.filing_summary_labels.items():
            lbl.configure(text=str(counts[key]))
        last_changed = self.app.db.get_filing_last_changed(client_id)
        self.filing_last_changed_label.configure(text=f"Last changed: {last_changed}" if last_changed else "")
