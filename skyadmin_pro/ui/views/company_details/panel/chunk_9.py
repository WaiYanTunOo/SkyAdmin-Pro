"""Company Details panel — per-company services, tax, VO/CSH, and documents."""

from __future__ import annotations

from skyadmin_pro.config import (
    TAX_FILING_FIELDS,
    TAX_FILING_LABELS,
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
            self.filing_history_tree.apply_theme()
            self.filing_history_tree.set_rows([], empty_message="Select a client to view filing history.")
            return

        counts = {"complete": 0, "ongoing": 0, "pending": 0, "na": 0}
        self._filing_suspend_save = True
        try:
            for field in TAX_FILING_FIELDS:
                val = (client or {}).get(field) or "Not Applicable"
                if val not in TAX_FILING_STATUSES:
                    val = "Not Applicable"
                self.filing_vars[field].set(val)
                self.filing_labels[field].configure(
                    text="\u2705"
                    if val == "Complete"
                    else "\U0001f7e1"
                    if val == "On-Going"
                    else "\u274c"
                    if val == "Pending"
                    else "\u2b1c"
                )
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
        self.filing_history_tree.apply_theme()
        history = self.app.db.get_filing_change_history(client_id)
        hist_rows, hist_iids = [], []
        for h in history:
            hist_rows.append(
                (
                    h.get("changed_at") or "",
                    TAX_FILING_LABELS.get(h.get("field") or "", h.get("field") or ""),
                    h.get("old_value") or "—",
                    h.get("new_value") or "—",
                )
            )
            hist_iids.append(str(h["id"]))
        self.filing_history_tree.set_rows(
            hist_rows,
            iids=hist_iids,
            empty_message="No filing status changes recorded yet.",
        )
