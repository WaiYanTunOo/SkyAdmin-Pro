"""Jump helper: Companies → Company Details → Filing Statuses."""

from __future__ import annotations

from skyadmin_pro.ui.views.company_details.panel import SUBTAB_FILING

from ._const_4 import TAB_COMPANY


class OpenCompanyFilingMixin:
    def open_company_filing(self, client_name: str) -> None:
        self.tabs.set(TAB_COMPANY)
        panel = self._require_company_panel()
        panel.select_client(client_name)
        panel.tabs.set(SUBTAB_FILING)
        self.refresh_active_tab(TAB_COMPANY)
