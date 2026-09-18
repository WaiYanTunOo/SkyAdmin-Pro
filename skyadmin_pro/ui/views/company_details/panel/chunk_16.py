"""Company Details panel — per-company services, tax, VO/CSH, and documents."""

from __future__ import annotations

from pathlib import Path

# Sub-tab names — single source of truth for the tab bar, lazy loader,
# refresh dispatcher, and cross-module callers (database_tasks/view.py).
from skyadmin_pro.ui.views.company_details.constants import (
    SUBTAB_GENERAL,
)


class CompanyDetailsPanelMixin16:
    def _save_document(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        try:
            expiry = self._parse_date(self.doc_expiry)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        file_name = self.doc_file.get().strip()
        saved_path = None
        picked = self.doc_path.get().strip()
        if picked:
            source = Path(picked)
            if not source.is_file():
                self.feedback.error("The picked file no longer exists.")
                return
            try:
                client_name = self.company_box.get().strip()
                from skyadmin_pro.ui.views.company_details import panel as panel_mod

                folder = panel_mod.create_client_workspace(self.app.paths.clients, client_name)
                saved = panel_mod.copy_file(source, folder)
            except Exception as exc:
                self.feedback.error(str(exc))
                return
            saved_path = str(saved)
            file_name = file_name or saved.name
        if self._editing_doc_id is None:
            self.app.db.record_document(
                client_id=client_id,
                document_type=self.doc_type.get(),
                file_name=file_name,
                file_path=saved_path or "",
                expiry_date=expiry,
            )
            self.feedback.success("Document record saved.")
        else:
            self.app.db.update_document(
                self._editing_doc_id,
                document_type=self.doc_type.get(),
                expiry_date=expiry,
                file_name=file_name,
                file_path=saved_path,
                clear=True,
            )
            self.feedback.success("Document record updated.")
        self._editing_doc_id = None
        self.document_status_label.configure(text="New document record")
        self.doc_expiry.set("")
        self.doc_file.set("")
        self.doc_path.set("")
        self._refresh_after_mutation(SUBTAB_GENERAL)
