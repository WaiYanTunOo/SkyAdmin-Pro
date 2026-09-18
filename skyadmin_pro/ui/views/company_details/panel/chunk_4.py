"""Company Details panel — per-company services, tax, VO/CSH, and documents."""

from __future__ import annotations

from skyadmin_pro.ui.combo_utils import fill_combo

# Sub-tab names — single source of truth for the tab bar, lazy loader,
# refresh dispatcher, and cross-module callers (database_tasks/view.py).


class CompanyDetailsPanelMixin4:
    def _selected_client_id(self) -> int | None:
        name = self.company_box.get().strip()
        if not name:
            return None
        # Lookup only — never create a client as a side effect of reading.
        return self.app.db.client_id_by_name(name)

    def select_client(self, name: str) -> None:
        self._fill_combo(name)

    def _fill_combo(self, current: str) -> None:
        names = self.app.db.list_client_names()
        fill_combo(self.company_box, names, current)

    def _on_company(self, _choice: str) -> None:
        self._cancel_service_edit()
        self._cancel_document_edit()
        self.refresh()

    def _update_company_info_line(
        self,
        client_id: int | None,
        *,
        service_count: int | None = None,
        document_count: int | None = None,
    ) -> None:
        if client_id is None:
            self.company_info.configure(text="Select a company to see services and documents.")
            return
        if service_count is None:
            service_count = len(self.app.db.list_client_services(client_id))
        if document_count is None:
            document_count = len(self.app.db.list_client_documents(client_id))
        self.company_info.configure(text=f"{service_count} service(s) \u00b7 {document_count} document(s)")
