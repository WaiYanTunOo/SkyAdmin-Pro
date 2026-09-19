"""Monthly service close — month package tracker (not form flags)."""

from __future__ import annotations

from skyadmin_pro.config import NAV_DATABASE_TASKS
from skyadmin_pro.ui.views.database_tasks.view.funcs import open_menu_view
from skyadmin_pro.ui.widgets import MonthStatusPanel

from .host import PanelHostView


class TaxStatusMenuView(PanelHostView):
    title = "Monthly Service Close"
    subtitle = (
        "Monthly FS + tax package for the month: Open, In progress, Closed. "
        "Form-level PND/PP30 flags live under Filing Statuses."
    )

    def _make_panel(self):
        panel = MonthStatusPanel(
            self.panel_parent,
            self.app,
            showheight=12,
            title="Monthly service close — FS & tax package for the month",
            on_open_filing=self._open_filing_statuses,
        )
        panel.grid_rowconfigure(1, weight=1)
        return panel

    def _open_filing_statuses(self, client_name: str) -> None:
        open_menu_view(self.app, NAV_DATABASE_TASKS, "open_company_filing", client_name)
