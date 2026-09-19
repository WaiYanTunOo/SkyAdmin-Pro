"""Dashboard card jumps target the correct Companies / Money destinations."""

from pathlib import Path


def _src(*parts: str) -> str:
    return (Path(__file__).resolve().parents[1].joinpath(*parts)).read_text(encoding="utf-8")


def test_dashboard_stat_card_commands_use_jump_helpers():
    tabs = _src("skyadmin_pro", "ui", "views", "dashboard", "tabs.py")
    assert "open_expiry(view.app)" in tabs
    assert "open_company_details_tab(view.app)" in tabs
    assert "open_clients_tab(view.app)" in tabs
    assert "open_filing_statuses(view.app)" in tabs
    assert "open_money_tab(view)" in tabs
    assert "open_vo_csh_setup(view.app)" in tabs
    assert "open_pipeline(view.app)" in tabs  # Ongoing services → Service Pipeline
    assert "show_view(NAV_SUPPLIERS)" in tabs  # Supplier due stays on Suppliers
    assert "show_view(NAV_DASHBOARD)" not in tabs
    assert "show_view(NAV_TAX_STATUS)" not in tabs
    assert "show_view(NAV_DATABASE_TASKS)" not in tabs


def test_money_tax_overview_open_goes_to_monthly_service_close():
    money = _src("skyadmin_pro", "ui", "views", "dashboard", "money_lines.py")
    assert "open_tax_status(view.app)" in money
    assert "open_filing_statuses(view.app)" in money
    assert "Monthly Service Close" in money
    assert "Tax overview" in money
    assert "Run Monthly Cycle" in money


def test_companies_open_tab_helpers_exist():
    helpers = _src("skyadmin_pro", "ui", "views", "database_tasks", "view", "open_company_tabs.py")
    assert "def open_expiry(self)" in helpers
    assert "def open_clients_tab(self)" in helpers
    assert "def open_company_details_tab(self)" in helpers
    assert "def open_filing_statuses(self)" in helpers
    assert "SUBTAB_FILING" in helpers
    init = _src("skyadmin_pro", "ui", "views", "database_tasks", "view", "__init__.py")
    assert "OpenCompanyTabsMixin" in init


def test_dashboard_jump_helpers_exported():
    jumps = _src("skyadmin_pro", "ui", "views", "dashboard", "jumps.py")
    companies = _src("skyadmin_pro", "ui", "views", "dashboard", "jumps_companies.py")
    for name in (
        "open_expiry",
        "open_clients_tab",
        "open_company_details_tab",
        "open_filing_statuses",
        "open_vo_csh_setup",
        "open_money_tab",
    ):
        assert name in jumps
        assert f"def {name}" in companies or name in jumps
