"""Company Details panel — per-company services, tax, VO/CSH, and documents."""

from __future__ import annotations

# Sub-tab names — single source of truth for the tab bar, lazy loader,
# refresh dispatcher, and cross-module callers (database_tasks/view.py).
from skyadmin_pro.ui.views.company_details.constants import (
    SUBTAB_GENERAL,
)


class CompanyDetailsPanelMixin5:
    def refresh(self) -> None:
        """Refresh company selector, header, and the active sub-tab."""
        self.refresh_active_subtab(update_combo=True, update_header=True)

    def refresh_active_subtab(self, *, update_combo: bool = False, update_header: bool = True) -> None:
        """Reload only the visible Company Details sub-tab."""
        if update_combo:
            self._fill_combo(self.company_box.get())
        client_id = self._selected_client_id()
        if update_header:
            self._update_company_info_line(client_id)
        tab = self._current_subtab()
        self._ensure_panel(tab)
        client = self.app.db.get_client(client_id) if client_id is not None else None
        self._refresh_subtab(tab, client_id, client)

    def _refresh_after_mutation(self, tab_name: str) -> None:
        """Single parameterized post-edit refresh: reload one sub-tab, then invalidate dashboard."""
        client_id = self._selected_client_id()
        client = self.app.db.get_client(client_id) if client_id is not None else None
        if tab_name == SUBTAB_GENERAL:
            services = self.app.db.list_client_services(client_id) if client_id is not None else []
            documents = self.app.db.list_client_documents(client_id) if client_id is not None else []
            self._update_company_info_line(
                client_id,
                service_count=len(services),
                document_count=len(documents),
            )
            self._refresh_subtab(tab_name, client_id, client, services=services, documents=documents)
        else:
            self._refresh_subtab(tab_name, client_id, client)
        self.app.invalidate_dashboard()
