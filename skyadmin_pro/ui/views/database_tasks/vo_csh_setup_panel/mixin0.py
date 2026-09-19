"""VO/CSH Setup rollout table and open-selected action."""

from __future__ import annotations

from skyadmin_pro.services.vo_csh_rollout import list_vo_csh_setup_rows
from skyadmin_pro.ui.setup_rollout import RolloutAction, SetupRolloutPanel


class VoCshSetupPanelMixin0:
    def _build_vo_csh_setup(self, master) -> SetupRolloutPanel:
        panel = SetupRolloutPanel(
            master,
            title="Virtual office & Thai shareholder",
            description=(
                "Firm-wide VO/CSH queue. Infer renewal dates from document expiry, "
                "then open Company Details → VO & CSH for providers."
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
            table_id="vo_csh.setup",
            db=self.app.db,
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
        if hasattr(self, "_vo_csh_setup_panel"):
            self._vo_csh_setup_panel.refresh()

    def refresh(self) -> None:
        self.refresh_vo_csh_setup()

    def _selected_vo_csh_setup_row(self) -> dict | None:
        if not hasattr(self, "_vo_csh_setup_panel"):
            return None
        return self._vo_csh_setup_panel.selected_row()

    def _open_selected_vo_csh_tab(self, _iid: str | None = None) -> None:
        row = self._selected_vo_csh_setup_row()
        if not row:
            self.feedback.error("Select a client first.")
            return
        name = (row.get("name") or "").strip()
        view = self.app.get_view("database_tasks")
        if view is not None and hasattr(view, "open_company_vo_csh"):
            view.open_company_vo_csh(name)
