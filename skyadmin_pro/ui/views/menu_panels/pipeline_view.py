"""New-job tracker, moved out of Database & Tasks. Same ServicePipelinePanel."""

from __future__ import annotations

from skyadmin_pro.ui.views.database_tasks.pipeline_panel import ServicePipelinePanel

from .host import PanelHostView


class PipelineMenuView(PanelHostView):
    title = "Service Pipeline"
    subtitle = "Nine steps for a new job, from appointment to done. Not the daily to-do list."

    def _make_panel(self):
        return ServicePipelinePanel(self.panel_parent, self.app, self.feedback)

    def open_pipeline(self) -> None:
        self.panel.refresh()

    def open_item(self, item_id: int) -> None:
        self.panel._page = 0
        self.panel._pending_select = int(item_id)
        self.panel.refresh()
