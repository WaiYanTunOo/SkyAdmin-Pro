"""Jump helpers: Companies tabs without requiring a client name."""

from __future__ import annotations

from skyadmin_pro.ui.views.company_details.panel import SUBTAB_FILING

from ._const_2 import TAB_CLIENTS, TAB_EXPIRY
from ._const_4 import TAB_COMPANY


class OpenCompanyTabsMixin:
    def open_expiry(self) -> None:
        self.tabs.set(TAB_EXPIRY)
        self._ensure_panel(TAB_EXPIRY)
        self.refresh_active_tab(TAB_EXPIRY)

    def open_clients_tab(self) -> None:
        self.tabs.set(TAB_CLIENTS)
        self._ensure_panel(TAB_CLIENTS)
        self.refresh_active_tab(TAB_CLIENTS)

    def open_company_details_tab(self) -> None:
        self.tabs.set(TAB_COMPANY)
        self._require_company_panel()
        self.refresh_active_tab(TAB_COMPANY)

    def open_filing_statuses(self) -> None:
        self.tabs.set(TAB_COMPANY)
        panel = self._require_company_panel()
        panel.tabs.set(SUBTAB_FILING)
        self.refresh_active_tab(TAB_COMPANY)
