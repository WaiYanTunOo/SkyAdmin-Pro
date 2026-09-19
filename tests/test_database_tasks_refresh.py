"""Database & Tasks refresh routing — active tab only."""

from __future__ import annotations

from unittest.mock import MagicMock

from skyadmin_pro.ui.views.database_tasks.view import DatabaseTasksView, service_menu_panel_key


def test_service_menu_panel_key_maps_tabs_with_combos():
    assert service_menu_panel_key("Clients & Expiry") == "clients"
    assert service_menu_panel_key("Company Details") == "company"
    assert service_menu_panel_key("Service Pipeline") is None


def test_service_menu_panel_key_ignores_tabs_without_service_combo():
    for tab in (
        "Tasks",
        "Courier Tracker",
        "Monthly Tax Status",
        "Renewals",
        "Suppliers & AP",
        "",
    ):
        assert service_menu_panel_key(tab) is None


def test_refresh_active_tab_only_hits_selected_panel(monkeypatch):
    view = DatabaseTasksView.__new__(DatabaseTasksView)
    view.clients_panel = MagicMock()
    view.company_panel = MagicMock()
    view.renewals_panel = MagicMock()
    monkeypatch.setattr(view, "_refresh_service_menus", lambda _tab: None)

    view.refresh_active_tab("Clients & Expiry")
    view.clients_panel.refresh.assert_called_once()
    view.company_panel.refresh.assert_not_called()
    view.renewals_panel.refresh.assert_not_called()

    view.clients_panel.reset_mock()
    view.renewals_panel.reset_mock()
    view.refresh_active_tab("Renewals")
    view.renewals_panel.refresh.assert_called_once()
    view.clients_panel.refresh.assert_not_called()


def test_suppliers_panel_refreshes_only_active_subtab():
    from skyadmin_pro.ui.views.database_tasks.suppliers.panel import SuppliersPanel

    panel = SuppliersPanel.__new__(SuppliersPanel)
    panel._supplier_tabs = MagicMock()
    panel._supplier_tabs.get.return_value = "Payments (AP)"
    panel.directory = MagicMock()
    panel.services = MagicMock()
    panel.payments = MagicMock()

    panel.refresh_active_tab()
    panel.payments.refresh.assert_called_once()
    panel.directory.refresh.assert_not_called()
    panel.services.refresh.assert_not_called()
