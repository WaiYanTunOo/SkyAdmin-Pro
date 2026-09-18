"""Clients & expiry tab — company list, workspace, and document expiry tracking."""

from __future__ import annotations

from skyadmin_pro.services.file_ops import open_in_file_manager, parse_flexible_date
from skyadmin_pro.services.workflow import create_client_workspace


class ClientsExpiryPanelMixin11:
    def _open_client_folder(self) -> None:
        name = self._selected_client_name()
        if not name:
            self.feedback.error("Select a client row first.")
            return
        try:
            self.app.db.get_or_create_client(name)
            folder = create_client_workspace(self.app.paths.clients, name)
            open_in_file_manager(folder)
        except Exception as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success(f"Opened: {folder}")
        self.app.set_status(f"Opened client workspace: {folder}")

    def _open_suppliers(self) -> None:
        try:
            open_in_file_manager(self.app.paths.suppliers)
        except Exception as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success(f"Opened: {self.app.paths.suppliers}")

    def _view_company_details(self) -> None:
        name = self._selected_client_name()
        if not name:
            self.feedback.error("Select a client row first.")
            return
        view = self.app.get_view("database_tasks")
        if view is not None and hasattr(view, "open_company_details"):
            view.open_company_details(name)
            self.feedback.info(f"Showing details for {name}")

    def _add_expiry(self) -> None:
        client = self.expiry_client.get().strip()
        if not client:
            self.feedback.error("Choose or type a client name.")
            return
        expiry = parse_flexible_date(self.expiry_var.get())
        if not expiry:
            self.feedback.error("Enter a valid expiry date.")
            return
        try:
            client_id = self.app.db.get_or_create_client(client)
            self.app.db.record_document(
                client_id=client_id,
                document_type=self.expiry_type.get(),
                file_name="",
                file_path="",
                expiry_date=expiry,
            )
        except Exception as exc:
            self.feedback.error(f"Could not record expiry: {exc}")
            return
        self.feedback.success(f"Expiry recorded for {client} ({expiry}).")
        self.expiry_var.set("")
        self.refresh()
