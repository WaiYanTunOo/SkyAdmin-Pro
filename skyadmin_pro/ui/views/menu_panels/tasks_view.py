"""Today's work, moved out of Database & Tasks. Same TaskPanel, no data change."""

from __future__ import annotations

from skyadmin_pro.ui.views.database_tasks.task_panel import TaskPanel

from .host import PanelHostView


class TasksMenuView(PanelHostView):
    title = "Tasks"
    subtitle = "Today’s work queue. A sold job’s steps live in Service Pipeline."

    def _make_panel(self):
        return TaskPanel(self.panel_parent, self.app, self.feedback)

    def open_task(self, task_id: int) -> None:
        self.panel.select_task(task_id)

    def _on_shortcut_save(self) -> bool:
        self.panel._save()
        return True
