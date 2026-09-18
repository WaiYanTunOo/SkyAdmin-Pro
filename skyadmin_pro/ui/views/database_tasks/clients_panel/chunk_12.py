"""Clients & expiry tab — company list, workspace, and document expiry tracking."""

from __future__ import annotations

from tkinter import messagebox


class ClientsExpiryPanelMixin12:
    def _delete_document(self) -> None:
        iid = self.doc_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select an expiry record first.")
            return
        if not messagebox.askyesno(
            "Delete expiry record",
            "Delete this expiry record?\n\nLinked renewal tasks will also be removed.",
            parent=self.winfo_toplevel(),
        ):
            return
        self.app.db.delete_document(int(iid))
        self.feedback.success("Expiry record deleted.")
        self.refresh()
