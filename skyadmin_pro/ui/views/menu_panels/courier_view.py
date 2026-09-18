"""Send-out log, moved out of Database & Tasks. Same CourierPanel."""

from __future__ import annotations

from skyadmin_pro.ui.views.database_tasks.courier_panel import CourierPanel

from .host import PanelHostView


class CourierMenuView(PanelHostView):
    title = "Courier Tracker"
    subtitle = "Send-out log (Grab, Kerry, and so on). Not live tracking."

    def _make_panel(self):
        return CourierPanel(self.panel_parent, self.app, self.feedback)
