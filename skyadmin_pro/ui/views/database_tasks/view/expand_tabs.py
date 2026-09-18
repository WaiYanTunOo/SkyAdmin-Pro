"""All tabs fill the viewport — mount the correct panel for each tab name."""

from __future__ import annotations

from skyadmin_pro.ui.views.company_details import CompanyDetailsPanel
from skyadmin_pro.ui.views.database_tasks.accounting_setup_panel import AccountingSetupPanel
from skyadmin_pro.ui.views.database_tasks.clients_panel import ClientsExpiryPanel
from skyadmin_pro.ui.views.database_tasks.courier_panel import CourierPanel
from skyadmin_pro.ui.views.database_tasks.pipeline_panel import ServicePipelinePanel
from skyadmin_pro.ui.views.database_tasks.renewal_panel import RenewalPanel
from skyadmin_pro.ui.views.database_tasks.suppliers import SuppliersPanel
from skyadmin_pro.ui.views.database_tasks.task_panel import TaskPanel
from skyadmin_pro.ui.widgets import MonthStatusPanel

from ._const_0 import TAB_TASKS
from ._const_1 import TAB_COURIER
from ._const_2 import TAB_CLIENTS
from ._const_3 import TAB_MONTH
from ._const_4 import TAB_COMPANY
from ._const_5 import TAB_RENEWALS
from ._const_6 import TAB_PIPELINE
from ._const_7 import TAB_SUPPLIERS
from ._const_9 import TAB_ACCOUNTING

# All tabs mount directly on their tab frame (no wrapping CanvasScrollFrame).
# The inner panels own their own scroll surface if needed.
FILL_TABS = (
    TAB_TASKS,
    TAB_COURIER,
    TAB_CLIENTS,
    TAB_MONTH,
    TAB_COMPANY,
    TAB_ACCOUNTING,
    TAB_RENEWALS,
    TAB_PIPELINE,
    TAB_SUPPLIERS,
)


def mount_fill_panel(view, name: str, tab):
    """Instantiate and return the correct panel for *tab*."""
    if name == TAB_TASKS:
        view.tasks_panel = TaskPanel(tab, view.app, view.feedback)
        return view.tasks_panel
    if name == TAB_COURIER:
        view.courier_panel = CourierPanel(tab, view.app, view.feedback)
        return view.courier_panel
    if name == TAB_CLIENTS:
        view.clients_panel = ClientsExpiryPanel(tab, view.app, view.feedback)
        return view.clients_panel
    if name == TAB_MONTH:
        panel = MonthStatusPanel(tab, view.app, showheight=12, title="Month close — not PND or PP30 flags")
        panel.grid_rowconfigure(1, weight=1)
        view.month_panel = panel
        return view.month_panel
    if name == TAB_COMPANY:
        view.company_panel = CompanyDetailsPanel(tab, view.app, view.feedback)
        return view.company_panel
    if name == TAB_ACCOUNTING:
        view.accounting_setup_panel = AccountingSetupPanel(tab, view.app, view.feedback)
        return view.accounting_setup_panel
    if name == TAB_PIPELINE:
        view.pipeline_panel = ServicePipelinePanel(tab, view.app, view.feedback)
        return view.pipeline_panel
    if name == TAB_SUPPLIERS:
        view.suppliers_panel = SuppliersPanel(tab, view.app, view.feedback)
        return view.suppliers_panel
    # TAB_RENEWALS (fallthrough)
    view.renewals_panel = RenewalPanel(tab, view.app, view.feedback)
    return view.renewals_panel
