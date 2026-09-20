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
    panel._ensure_panel = MagicMock()
    panel._refresh_general_subtab = MagicMock()
    panel._refresh_tax_ids_subtab = MagicMock()
    panel._refresh_filing_subtab = MagicMock()
    panel._refresh_vo_csh_subtab = MagicMock()
    panel._refresh_financial_docs = MagicMock()
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


def test_cancel_service_edit_resets_editing_state_fully():
    panel = CompanyDetailsPanel.__new__(CompanyDetailsPanel)
    panel.app = MagicMock()
    panel.app.db.list_service_types.return_value = ["Accounting", "Auditing"]
    panel.service_type = MagicMock()
    panel.service_type.get.return_value = "Accounting"
    panel.service_start = MagicMock()
    panel.service_expiry = MagicMock()
    panel.service_payment = MagicMock()
    panel.service_amount = MagicMock()
    panel.service_progress = MagicMock()
    panel.service_paid = MagicMock()
    panel.service_status_label = MagicMock()
    panel._editing_service_id = 7
    panel._editing_doc_id = None

    panel._cancel_service_edit()

    assert panel._editing_service_id is None
    panel.service_status_label.configure.assert_called_once_with(text="New service record")
    panel.service_type.set.assert_called_once_with("Accounting")
    panel.service_start.set.assert_called_once_with("")
    panel.service_expiry.set.assert_called_once_with("")
    panel.service_payment.set.assert_called_once_with("")
    panel.service_amount.set.assert_called_once_with("")
    panel.service_progress.set.assert_called_once_with("Not started")
    panel.service_paid.deselect.assert_called_once()


def test_cancel_document_edit_resets_editing_state_fully():
    panel = CompanyDetailsPanel.__new__(CompanyDetailsPanel)
    panel.app = MagicMock()
    panel.doc_type = MagicMock()
    panel.doc_type.get.return_value = "Tax Returns"
    panel.doc_expiry = MagicMock()
    panel.doc_file = MagicMock()
    panel.doc_path = MagicMock()
    panel.document_status_label = MagicMock()
    panel._editing_doc_id = 9
    panel._editing_service_id = None

    panel._cancel_document_edit()

    assert panel._editing_doc_id is None
    panel.document_status_label.configure.assert_called_once_with(text="New document record")
    panel.doc_type.set.assert_called_once_with("Company Certificate")
    panel.doc_expiry.set.assert_called_once_with("")
    panel.doc_file.set.assert_called_once_with("")
    panel.doc_path.set.assert_called_once_with("")


def test_cancel_edit_idempotent_when_no_edit_in_progress():
    panel = CompanyDetailsPanel.__new__(CompanyDetailsPanel)
    panel.app = MagicMock()
    panel.app.db.list_service_types.return_value = ["Accounting"]
    panel._editing_service_id = None
    panel._editing_doc_id = None
    panel.service_type = MagicMock()
    panel.service_status_label = MagicMock()
    panel.doc_type = MagicMock()
    panel.document_status_label = MagicMock()
    panel.service_start = MagicMock()
    panel.service_expiry = MagicMock()
    panel.service_payment = MagicMock()
    panel.service_amount = MagicMock()
    panel.service_progress = MagicMock()
    panel.service_paid = MagicMock()
    panel.doc_expiry = MagicMock()
    panel.doc_file = MagicMock()
    panel.doc_path = MagicMock()

    panel._cancel_service_edit()
    panel._cancel_document_edit()

    assert panel._editing_service_id is None
    assert panel._editing_doc_id is None
    panel.service_type.set.assert_called_once_with("Accounting")
    panel.doc_type.set.assert_called_once_with("Company Certificate")
