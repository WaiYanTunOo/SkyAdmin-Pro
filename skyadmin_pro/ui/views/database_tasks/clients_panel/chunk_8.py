"""Clients & expiry tab — company list, workspace, and document expiry tracking."""

from __future__ import annotations

from tkinter import messagebox

from skyadmin_pro.services.file_ops import open_in_file_manager
from skyadmin_pro.services.workflow import create_client_workspace


class ClientsExpiryPanelMixin8:
    def _undo_last(self) -> None:
        if not self._undo.can_undo():
            self.feedback.info("Nothing to undo.")
            return
        conflicts = self._undo.preview_conflicts()
        force = False
        if conflicts:
            from tkinter import messagebox

            if not messagebox.askyesno(
                "Undo will overwrite",
                "Undoing would overwrite rows created after the delete:\n\n"
                + "\n".join(f"• {c}" for c in conflicts)
                + "\n\nOverwrite them?",
                parent=self.winfo_toplevel(),
            ):
                return
            force = True
        try:
            label = self._undo.undo(force=force)
        except Exception as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success(f"Undid: {label}.")
        self.refresh()

    def _on_shortcut_undo(self) -> None:
        self._undo_last()

    def _generate_workspace(self) -> None:
        name = self._selected_client_name()
        if not name:
            self.feedback.error("Select a client row to generate its workspace.")
            return
        try:
            self.app.db.get_or_create_client(name)
            folder = create_client_workspace(self.app.paths.clients, name)
        except Exception as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success(f"Workspace ready: {folder.name}/01_Company_Setup, 02_Accounting, 03_Visa")
        self.refresh()
        try:
            open_in_file_manager(folder)
        except Exception as exc:
            self.feedback.info(str(exc))

    def _delete_client(self) -> None:
        iid = self.client_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a client first.")
            return
        if not messagebox.askyesno(
            "Delete client",
            "Delete this client? Its pipeline, renewal checklists, and month-close "
            "records are removed. Services, documents, and tasks keep their records "
            "but lose the client link. You can undo once with Ctrl+Z.",
            parent=self.winfo_toplevel(),
        ):
            return
        from skyadmin_pro.services.client_commands import DeleteClientsCommand

        self._undo.execute(DeleteClientsCommand(self.app.db, [int(iid)]))
        self.feedback.success("Client deleted. (Ctrl+Z to undo)")
        self.refresh()
