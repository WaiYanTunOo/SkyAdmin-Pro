"""VO/CSH Setup — infer renewal dates (selected + bulk)."""

from __future__ import annotations

from tkinter import messagebox

from skyadmin_pro.services.vo_csh_rollout import (
    infer_client_vo_csh_renewal_dates,
    infer_vo_csh_renewal_dates,
    list_vo_csh_setup_rows,
)


class VoCshSetupPanelMixin1:
    def _infer_selected_vo_csh_dates(self) -> None:
        row = self._selected_vo_csh_setup_row()
        if not row:
            self.feedback.error("Select a client first.")
            return
        if not row.get("can_infer_vo") and not row.get("can_infer_csh"):
            self.feedback.error("No document expiry dates available to infer.")
            return
        result = infer_client_vo_csh_renewal_dates(self.app.db, int(row["id"]))
        total = int(result["vo"]) + int(result["csh"])
        if not total:
            self.feedback.info("Nothing to infer for this client.")
            return
        self.feedback.success(f"Inferred {result['vo']} VO and {result['csh']} CSH renewal date(s).")
        self.refresh_vo_csh_setup()

    def _infer_all_vo_csh_dates(self) -> None:
        pending = sum(
            1 for row in list_vo_csh_setup_rows(self.app.db) if row.get("can_infer_vo") or row.get("can_infer_csh")
        )
        if pending == 0:
            self.feedback.info("No clients need renewal date inference.")
            return
        if not messagebox.askyesno(
            "Infer VO/CSH renewal dates",
            f"Infer renewal dates from document expiry for {pending} client(s)?",
            parent=self.winfo_toplevel(),
        ):
            return
        result = infer_vo_csh_renewal_dates(self.app.db, only_missing=True)
        total = int(result["vo"]) + int(result["csh"])
        self.feedback.success(f"Inferred {result['vo']} VO and {result['csh']} CSH renewal date(s) ({total} total).")
        self.refresh_vo_csh_setup()
