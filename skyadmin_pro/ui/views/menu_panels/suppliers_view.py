"""Vendors and bills, moved out of Database & Tasks. Same SuppliersPanel."""

from __future__ import annotations

from skyadmin_pro.ui.views.database_tasks.suppliers_panel import SuppliersPanel

from .host import PanelHostView


class SuppliersMenuView(PanelHostView):
    title = "Suppliers & AP"
    subtitle = "Vendors and bills this firm owes. Not Office Hub contacts."

    def _make_panel(self):
        return SuppliersPanel(self.panel_parent, self.app, self.feedback)
