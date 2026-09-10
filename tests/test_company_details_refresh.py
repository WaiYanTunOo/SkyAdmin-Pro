"""Company Details active-subtab refresh tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from skyadmin_pro.ui.views.company_details.constants import (
    SUBTAB_FILING,
    SUBTAB_GENERAL,
    SUBTAB_TAX_IDS,
)
from skyadmin_pro.ui.views.company_details.panel import CompanyDetailsPanel


def _panel_with_tabs(current_tab: str) -> CompanyDetailsPanel:
    panel = CompanyDetailsPanel.__new__(CompanyDetailsPanel)
    panel.app = MagicMock()
    panel.company_box = MagicMock()
    panel.company_box.get.return_value = "Acme Co"
    panel.company_info = MagicMock()
    panel.tabs = MagicMock()
    panel.tabs.get.return_value = current_tab
    panel._lazy_tabs = {current_tab}
    panel._ensure_lazy_tab = MagicMock()
    panel._refresh_general_subtab = MagicMock()
    panel._refresh_tax_ids_subtab = MagicMock()
    panel._refresh_filing_subtab = MagicMock()
    panel._refresh_vo_csh_subtab = MagicMock()
    panel._refresh_financial_docs = MagicMock()
    panel.refresh_accounting_setup = MagicMock()
    panel.refresh_vo_csh_setup = MagicMock()
    # Don't mock _refresh_after_mutation - we want to test the real method
    panel.app.invalidate_dashboard = MagicMock()
    panel._selected_client_id = MagicMock(return_value=1)
    panel.app.db.get_client.return_value = {"id": 1, "name": "Acme Co"}
    panel.app.db.list_client_services.return_value = [{"id": 1}]
    panel.app.db.list_client_documents.return_value = [{"id": 2}]
    return panel


def test_refresh_active_subtab_skips_service_queries_on_tax_ids():
    panel = _panel_with_tabs("Tax IDs")

    panel.refresh_active_subtab(update_header=False)

    panel.app.db.list_client_services.assert_not_called()
    panel.app.db.list_client_documents.assert_not_called()
    panel._refresh_tax_ids_subtab.assert_called_once()


def test_refresh_active_subtab_loads_services_only_for_general():
    panel = _panel_with_tabs("General")

    panel.refresh_active_subtab(update_header=False)

    panel.app.db.list_client_services.assert_called_once()
    panel.app.db.list_client_documents.assert_called_once()
    panel._refresh_general_subtab.assert_called_once()


def test_tax_ids_mutation_refreshes_only_tax_subtab():
    panel = _panel_with_tabs("Tax IDs")

    panel._refresh_after_mutation(SUBTAB_TAX_IDS)

    panel._refresh_tax_ids_subtab.assert_called_once()
    panel.app.db.list_client_services.assert_not_called()


def test_general_mutation_updates_header_counts():
    panel = _panel_with_tabs("General")
    panel._update_company_info_line = MagicMock()

    panel._refresh_after_mutation(SUBTAB_GENERAL)

    panel._update_company_info_line.assert_called_once_with(1, service_count=1, document_count=1)
    panel._refresh_general_subtab.assert_called_once()


def test_filing_mutation_refreshes_filing_subtab():
    panel = _panel_with_tabs("Filing")
    # Simulate the mutation call that FilingTabMixin would make
    panel._refresh_after_mutation(SUBTAB_FILING)

    panel._refresh_filing_subtab.assert_called_once_with(1, {"id": 1, "name": "Acme Co"})
    panel.app.invalidate_dashboard.assert_called_once()


def test_persist_filing_field_routes_history_through_mutation(monkeypatch):
    from skyadmin_pro.ui.views.company_details.filing_tab import FilingTabMixin

    panel = _panel_with_tabs("Filing")
    panel.filing_vars = {"fs_status": MagicMock()}
    panel.filing_vars["fs_status"].get.return_value = "Pending"
    panel.feedback = MagicMock()
    panel.app.db.get_client_tax_summary.return_value = {"fs_status": "Not Applicable"}
    panel._refresh_after_mutation = MagicMock()

    FilingTabMixin._persist_filing_field(panel, "fs_status")

    panel.app.db.log_tax_change.assert_called_once()
    panel.app.db.update_client_fields.assert_called_once()
    panel._refresh_after_mutation.assert_called_once_with(SUBTAB_FILING)
