"""Company Details panel — per-company services, tax, VO/CSH, and documents."""

from __future__ import annotations

from tkinter import messagebox

# Sub-tab names — single source of truth for the tab bar, lazy loader,
# refresh dispatcher, and cross-module callers (database_tasks/view.py).
from skyadmin_pro.ui.views.company_details.constants import (
    SUBTAB_GENERAL,
)


class CompanyDetailsPanelMixin17:
    def _delete_service(self) -> None:
        iid = self.service_tree.selected_iid()
        if not iid or iid == "__empty__" or not str(iid).isdigit():
            self.feedback.error("Select a service row first.")
            return
        if not messagebox.askyesno(
            "Delete service record", "Remove this service record?", parent=self.winfo_toplevel()
        ):
            return
        self.app.db.delete_document(int(iid))
        self.feedback.success("Service record deleted.")
        self._refresh_after_mutation(SUBTAB_GENERAL)

    def _delete_document(self) -> None:
        iid = self.doc_tree.selected_iid()
        if not iid or iid == "__empty__" or not str(iid).isdigit():
            self.feedback.error("Select a document row first.")
            return
        if not messagebox.askyesno(
            "Delete document record", "Remove this document record?", parent=self.winfo_toplevel()
        ):
            return
        self.app.db.delete_document(int(iid))
        self.feedback.success("Document record deleted.")
        self._refresh_after_mutation(SUBTAB_GENERAL)
