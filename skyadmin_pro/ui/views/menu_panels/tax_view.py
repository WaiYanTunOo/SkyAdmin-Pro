"""Month close, moved out of Database & Tasks. Same MonthStatusPanel."""

from __future__ import annotations

from skyadmin_pro.ui.widgets import MonthStatusPanel

from .host import PanelHostView


class TaxStatusMenuView(PanelHostView):
    title = "Monthly Tax Status"
    subtitle = "Month close only: Open, In progress, Closed. Not PND or PP30 flags."

    def _make_panel(self):
        panel = MonthStatusPanel(
            self.panel_parent,
            self.app,
            showheight=12,
            title="Month close — not PND or PP30 flags",
        )
        panel.grid_rowconfigure(1, weight=1)
        return panel
