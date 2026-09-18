"""Clients & expiry tab — company list, workspace, and document expiry tracking."""

from __future__ import annotations

from tkinter import messagebox

from skyadmin_pro.ui.theme import TEXT_MUTED


class ClientsExpiryPanelMixin9:
    def _on_client_tree_select(self, _event=None) -> None:
        if not hasattr(self, "_batch_selection_label"):
            return
        count = len(self.client_tree.selected_iids())
        if count > 0:
            self._batch_selection_label.configure(
                text=f"{count} selected",
                text_color=("#0284c7", "#38bdf8"),
            )
        else:
            self._batch_selection_label.configure(
                text="0 selected",
                text_color=TEXT_MUTED,
            )

    def _batch_delete(self) -> None:
        iids = self.client_tree.selected_iids()
        if not iids:
            self.feedback.error("Select one or more clients first.")
            return
        if not messagebox.askyesno(
            "Batch delete",
            f"Permanently delete {len(iids)} selected client(s)?\n\n"
            "This cannot be undone after leaving this screen (Ctrl+Z works once). "
            "Prefer Archive to soft-delete instead.",
            parent=self.winfo_toplevel(),
        ):
            return
        from skyadmin_pro.services.client_commands import DeleteClientsCommand

        ids = [int(iid) for iid in iids]
        count = self._undo.execute(DeleteClientsCommand(self.app.db, ids))
        self.feedback.success(f"Deleted {count} client(s). (Ctrl+Z to undo)")
        self.refresh()

    def _batch_archive(self) -> None:
        iids = self.client_tree.selected_iids()
        if not iids:
            self.feedback.error("Select one or more clients first.")
            return
        if not messagebox.askyesno(
            "Archive clients",
            f"Archive {len(iids)} selected client(s)?\n\n"
            "They are hidden from the company list (soft-delete). "
            "You can undo once with Ctrl+Z.",
            parent=self.winfo_toplevel(),
        ):
            return
        from skyadmin_pro.services.client_commands import ArchiveClientsCommand

        ids = [int(iid) for iid in iids]
        count = self._undo.execute(ArchiveClientsCommand(self.app.db, ids))
        self.feedback.success(f"Archived {count} client(s). (Ctrl+Z to undo)")
        self.refresh()

    def _batch_set_status(self, status: str) -> None:
        iids = self.client_tree.selected_iids()
        if not iids:
            self.feedback.error("Select one or more clients first.")
            return
        from skyadmin_pro.services.client_commands import SetStatusCommand

        ids = [int(iid) for iid in iids]
        count = self._undo.execute(SetStatusCommand(self.app.db, ids, status))
        label = "Active" if status.lower() == "active" else "Inactive"
        self.feedback.success(f"Updated {count} client(s) to {label}.")
        self.refresh()
