"""Accounting setup rollout tab for Company Details."""

from __future__ import annotations

from tkinter import messagebox

from skyadmin_pro.services.tax_ids_rollout import (
    apply_pricing_tier,
    infer_service_types,
    list_accounting_setup_rows,
    parse_document_types,
)
from skyadmin_pro.ui.setup_rollout import RolloutAction, SetupRolloutPanel


class AccountingSetupTabMixin:
    def _build_accounting_setup(self, master) -> SetupRolloutPanel:
        panel = SetupRolloutPanel(
            master,
            title="Accounting clients — Tax IDs rollout",
            description=(
                "Clients with annual/monthly accounting or tax-filing documents. "
                "Infer service type from documents, then open Tax IDs to set transaction "
                "volume, tax ID, and pricing."
            ),
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
        self.select_client(name)
        self.tabs.set("Tax IDs")
        self.refresh()

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
            self.refresh()

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
        self.refresh()

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
                self.refresh()
        else:
            self.feedback.error("No matching pricing tier — check Settings → Pricing matrix.")
