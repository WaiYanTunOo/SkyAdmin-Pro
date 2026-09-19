"""Companies tabs fill the viewport — mount the correct panel for each tab name."""

from __future__ import annotations

from skyadmin_pro.ui.views.company_details import CompanyDetailsPanel
from skyadmin_pro.ui.views.database_tasks.clients_panel import ClientsExpiryPanel
from skyadmin_pro.ui.views.database_tasks.renewal_panel import RenewalPanel
from skyadmin_pro.ui.views.database_tasks.vo_csh_setup_panel import VoCshSetupPanel

from ._const_2 import TAB_CLIENTS, TAB_EXPIRY
from ._const_4 import TAB_COMPANY
from ._const_5 import TAB_RENEWALS
from ._const_6 import TAB_VO_CSH_SETUP

# All tabs mount directly on their tab frame (no wrapping CanvasScrollFrame).
# The inner panels own their own scroll surface if needed.
FILL_TABS = (
    TAB_CLIENTS,
    TAB_EXPIRY,
    TAB_COMPANY,
    TAB_VO_CSH_SETUP,
    TAB_RENEWALS,
)


def mount_fill_panel(view, name: str, tab):
    """Instantiate and return the correct panel for *tab*."""
    if name == TAB_CLIENTS:
        view.clients_panel = ClientsExpiryPanel(tab, view.app, view.feedback, mode="clients")
        return view.clients_panel
    if name == TAB_EXPIRY:
        view.expiry_panel = ClientsExpiryPanel(tab, view.app, view.feedback, mode="expiry")
        return view.expiry_panel
    if name == TAB_COMPANY:
        view.company_panel = CompanyDetailsPanel(tab, view.app, view.feedback)
        return view.company_panel
    if name == TAB_VO_CSH_SETUP:
        view.vo_csh_setup_panel = VoCshSetupPanel(tab, view.app, view.feedback)
        return view.vo_csh_setup_panel
    # TAB_RENEWALS (fallthrough)
    view.renewals_panel = RenewalPanel(tab, view.app, view.feedback)
    return view.renewals_panel
