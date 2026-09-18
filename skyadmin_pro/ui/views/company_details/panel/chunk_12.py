"""Company Details panel — per-company services, tax, VO/CSH, and documents."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog

from skyadmin_pro.config import (
    IMPORTANT_DOC_TYPES,
)

# Sub-tab names — single source of truth for the tab bar, lazy loader,
# refresh dispatcher, and cross-module callers (database_tasks/view.py).


class CompanyDetailsPanelMixin12:
    def _edit_document(self, iid: str | None) -> None:
        if not iid or iid == "__empty__" or not str(iid).isdigit():
            return
        item = self.app.db.get_document(int(iid))
        if not item:
            return
        self._editing_doc_id = int(item["id"])
        self.document_status_label.configure(text="Editing document record — Save to update")
        if item.get("document_type") in IMPORTANT_DOC_TYPES:
            self.doc_type.set(item["document_type"])
        self.doc_expiry.set(item.get("expiry_date") or "")
        self.doc_file.set(item.get("file_name") or "")
        self.doc_path.set("")

    def _pick_document_file(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Pick document file",
            filetypes=[
                ("All files", "*.*"),
                ("PDF files", "*.pdf"),
                ("Images", "*.png *.jpg *.jpeg *.tif *.tiff"),
            ],
        )
        if path:
            self.doc_path.set(path)
            self.doc_file.set(Path(path).name)
