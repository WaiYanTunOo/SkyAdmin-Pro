"""Accounting clients rollout — Finance sidebar page."""

from __future__ import annotations

from skyadmin_pro.ui.views.database_tasks.accounting_setup_panel import AccountingSetupPanel

from .host import PanelHostView


class AccountingSetupMenuView(PanelHostView):
    title = "Accounting Setup"
    subtitle = "Accounting clients rollout — infer service type and Tax IDs readiness. Not month close."

    def _make_panel(self):
        return AccountingSetupPanel(self.panel_parent, self.app, self.feedback)
