"""Accounting Setup rollout — Companies main tab (not Company Details)."""

from __future__ import annotations

from skyadmin_pro.services.tax_ids_rollout import list_accounting_setup_rows, parse_document_types
from skyadmin_pro.ui.setup_rollout import RolloutAction, SetupRolloutPanel


class AccountingSetupPanelMixin0:
    def _build_accounting_setup(self, master) -> SetupRolloutPanel:
        panel = SetupRolloutPanel(
            master,
            title="Accounting clients — Tax IDs rollout",
            description=("How the firm infers the bought service from documents — not month close."),
            columns=(
                ("company", "Company", 220),
                ("status", "Setup", 90),
                ("service", "Service type", 140),
                ("suggested", "Suggested", 140),
                ("volume", "Txn volume", 170),
                ("tax_id", "Tax ID", 120),
                ("docs", "Accounting docs", 220),
            ),
            actions=(
                RolloutAction("Open Tax IDs", self._open_selected_accounting_tax_ids, width=120),
                RolloutAction("Infer service type", self._infer_selected_service_type, width=140),
                RolloutAction(
                    "Infer all missing",
                    self._infer_all_service_types,
                    width=130,
                    fg_color="transparent",
                    border_width=1,
                ),
                RolloutAction(
                    "Apply pricing tier",
                    self._apply_selected_pricing_tier,
                    width=140,
                    fg_color="transparent",
                    border_width=1,
                ),
            ),
            on_double_click=self._open_selected_accounting_tax_ids,
            showheight=10,
            tree_sticky="nsew",
            tree_row_weight=1,
            table_id="accounting.setup",
            db=self.app.db,
        )
        panel.configure_data(
            list_rows=lambda: list_accounting_setup_rows(self.app.db),
            row_cells=self._accounting_setup_cells,
            summary=lambda ready, total: f"{ready} of {total} accounting client(s) ready for tax cycle",
        )
        self._accounting_setup_panel = panel
        return panel

    def _accounting_setup_cells(self, row: dict) -> tuple:
        docs = parse_document_types(row.get("document_types"))
        short_docs = docs[0] if len(docs) == 1 else f"{len(docs)} doc type(s)" if docs else "—"
        return (
            row.get("name") or "",
            row.get("setup_status") or "",
            row.get("service_type") or "—",
            row.get("suggested_service_type") or "—",
            row.get("num_transactions") or "—",
            row.get("tax_id") or "—",
            short_docs,
        )

    def refresh_accounting_setup(self) -> None:
        if hasattr(self, "_accounting_setup_panel"):
            self._accounting_setup_panel.refresh()

    def refresh(self) -> None:
        self.refresh_accounting_setup()

    def _selected_accounting_setup_row(self) -> dict | None:
        if not hasattr(self, "_accounting_setup_panel"):
            return None
        return self._accounting_setup_panel.selected_row()

    def _open_selected_accounting_tax_ids(self, _iid: str | None = None) -> None:
        row = self._selected_accounting_setup_row()
        if not row:
            self.feedback.error("Select an accounting client first.")
            return
        name = (row.get("name") or "").strip()
        view = self.app.get_view("database_tasks")
        if view is not None and hasattr(view, "open_company_tax_ids"):
            view.open_company_tax_ids(name)
