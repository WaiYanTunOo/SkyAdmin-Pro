"""Company-file tabs that fill the viewport — no outer CanvasScrollFrame."""

from __future__ import annotations

from skyadmin_pro.ui.views.company_details import CompanyDetailsPanel
from skyadmin_pro.ui.views.database_tasks.accounting_setup_panel import AccountingSetupPanel
from skyadmin_pro.ui.views.database_tasks.clients_panel import ClientsExpiryPanel
from skyadmin_pro.ui.views.database_tasks.renewal_panel import RenewalPanel

from ._const_2 import TAB_CLIENTS
from ._const_4 import TAB_COMPANY
from ._const_5 import TAB_RENEWALS
from ._const_9 import TAB_ACCOUNTING

FILL_TABS = (TAB_CLIENTS, TAB_COMPANY, TAB_ACCOUNTING, TAB_RENEWALS)


def mount_fill_panel(view, name: str, tab):
    """Parent a panel on the tab so it can expand. Returns the panel."""
    if name == TAB_COMPANY:
        view.company_panel = CompanyDetailsPanel(tab, view.app, view.feedback)
        return view.company_panel
    if name == TAB_ACCOUNTING:
        view.accounting_setup_panel = AccountingSetupPanel(tab, view.app, view.feedback)
        return view.accounting_setup_panel
    if name == TAB_CLIENTS:
        view.clients_panel = ClientsExpiryPanel(tab, view.app, view.feedback)
        return view.clients_panel
    view.renewals_panel = RenewalPanel(tab, view.app, view.feedback)
    return view.renewals_panel
