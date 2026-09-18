"""Company Details panel — per-company services, tax, VO/CSH, and documents."""

from __future__ import annotations

from skyadmin_pro.ui.views.company_details.constants import (
    SUBTAB_FILING,
    SUBTAB_FINANCIAL_DOCS,
    SUBTAB_GENERAL,
    SUBTAB_TAX_IDS,
    SUBTAB_VO_CSH,
    SUBTAB_VO_CSH_SETUP,
)


class CompanyDetailsPanelMixin6:
    def _refresh_subtab(
        self,
        tab_name: str,
        client_id: int | None,
        client: dict | None,
        *,
        services: list | None = None,
        documents: list | None = None,
    ) -> None:
        if tab_name == SUBTAB_GENERAL:
            if services is None:
                services = self.app.db.list_client_services(client_id) if client_id is not None else []
            if documents is None:
                documents = self.app.db.list_client_documents(client_id) if client_id is not None else []
            self._refresh_general_subtab(client_id, client, services, documents)
        elif tab_name == SUBTAB_TAX_IDS:
            self._refresh_tax_ids_subtab(client_id, client)
        elif tab_name == SUBTAB_FILING:
            self._refresh_filing_subtab(client_id, client)
        elif tab_name == SUBTAB_VO_CSH_SETUP:
            self.refresh_vo_csh_setup()
        elif tab_name == SUBTAB_VO_CSH:
            self._refresh_vo_csh_subtab(client)
        elif tab_name == SUBTAB_FINANCIAL_DOCS:
            self._refresh_financial_docs()
