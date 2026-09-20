"""Company Details panel — per-company services, tax, VO/CSH, and documents."""

from __future__ import annotations

from skyadmin_pro.config import (
    IMPORTANT_DOC_TYPES,
    SERVICE_PROGRESS,
)

# Sub-tab names — single source of truth for the tab bar, lazy loader,
# refresh dispatcher, and cross-module callers (database_tasks/view.py).


class CompanyDetailsPanelMixin11:
    def _cancel_document_edit(self) -> None:
        self._editing_doc_id = None
        if hasattr(self, "document_status_label"):
            self.document_status_label.configure(text="New document record")
        if hasattr(self, "doc_type"):
            self.doc_type.set(IMPORTANT_DOC_TYPES[0])
        if hasattr(self, "doc_expiry"):
            self.doc_expiry.set("")
            self.doc_file.set("")
            self.doc_path.set("")

    def _edit_service(self, iid: str | None) -> None:
        if not iid or iid == "__empty__" or not str(iid).isdigit():
            return
        item = self.app.db.get_document(int(iid))
        if not item:
            return
        self._editing_service_id = int(item["id"])
        self.service_status_label.configure(text="Editing service record — Save to update")
        if item.get("document_type") in self.app.db.list_service_types():
            self.service_type.set(item["document_type"])
        self.service_start.set(item.get("start_date") or "")
        self.service_expiry.set(item.get("expiry_date") or "")
        self.service_payment.set(item.get("payment_date") or "")
        self.service_amount.set(item.get("amount") or "")
        progress = item.get("progress") or "Not started"
        if progress not in SERVICE_PROGRESS:
            progress = "Not started"
        self.service_progress.set(progress)
        if item.get("paid"):
            self.service_paid.select()
        else:
            self.service_paid.deselect()
