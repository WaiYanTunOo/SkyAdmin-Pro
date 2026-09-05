"""VO/CSH setup rollout tab for Company Details."""

from __future__ import annotations

from tkinter import messagebox

from skyadmin_pro.services.vo_csh_rollout import (
    infer_client_vo_csh_renewal_dates,
    infer_vo_csh_renewal_dates,
    list_vo_csh_setup_rows,
)
from skyadmin_pro.ui.setup_rollout import RolloutAction, SetupRolloutPanel


class VoCshSetupTabMixin:
    def _build_vo_csh_setup(self, master) -> SetupRolloutPanel:
        panel = SetupRolloutPanel(
            master,
            title="VO / CSH renewal rollout",
            description=(
                "Clients with Virtual Office or CSH rental documents. Infer renewal dates "
                "from document expiry, then review providers and addresses on the VO & CSH tab."
            ),
            columns=(
                ("company", "Company", 200),
                ("status", "Setup", 80),
                ("vo_docs", "VO docs", 70),
                ("vo_date", "VO renewal", 100),
                ("vo_suggest", "Suggested VO", 100),
                ("csh_docs", "CSH docs", 70),
                ("csh_date", "CSH renewal", 100),
                ("csh_suggest", "Suggested CSH", 100),
            ),
            actions=(
                RolloutAction("Open VO & CSH", self._open_selected_vo_csh_tab, width=130),
                RolloutAction("Infer renewal dates", self._infer_selected_vo_csh_dates, width=150),
                RolloutAction(
                    "Infer all missing",
                    self._infer_all_vo_csh_dates,
                    width=130,
                    fg_color="transparent",
                    border_width=1,
                ),
            ),
            on_double_click=self._open_selected_vo_csh_tab,
            showheight=10,
            tree_sticky="nsew",
            tree_row_weight=1,
        )
        panel.configure_data(
            list_rows=lambda: list_vo_csh_setup_rows(self.app.db),
            row_cells=self._vo_csh_setup_cells,
            summary=lambda ready, total: f"{ready} of {total} VO/CSH client(s) have renewal dates set",
        )
        self._vo_csh_setup_panel = panel
        return panel

    def _vo_csh_setup_cells(self, row: dict) -> tuple:
        return (
            row.get("name") or "",
            row.get("setup_status") or "",
            str(int(row.get("vo_doc_count") or 0)),
            row.get("vo_renewal_date") or "—",
            row.get("suggested_vo_renewal_date") or "—",
            str(int(row.get("csh_doc_count") or 0)),
            row.get("csh_renewal_date") or "—",
            row.get("suggested_csh_renewal_date") or "—",
        )

    def refresh_vo_csh_setup(self) -> None:
        if hasattr(self, "_ensure_lazy_tab"):
            self._ensure_lazy_tab("VO/CSH Setup")
        if hasattr(self, "_vo_csh_setup_panel"):
            self._vo_csh_setup_panel.refresh()

    def _selected_vo_csh_setup_row(self) -> dict | None:
        if not hasattr(self, "_vo_csh_setup_panel"):
            return None
        return self._vo_csh_setup_panel.selected_row()

    def _open_selected_vo_csh_tab(self, _iid: str | None = None) -> None:
        row = self._selected_vo_csh_setup_row()
        if not row:
            self.feedback.error("Select a client first.")
            return
        self.select_client((row.get("name") or "").strip())
        self.tabs.set("VO & CSH")
        self.refresh()

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
        if self._selected_client_id() == int(row["id"]) and self._current_subtab() == "VO & CSH":
            self._refresh_vo_csh_mutation()

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
