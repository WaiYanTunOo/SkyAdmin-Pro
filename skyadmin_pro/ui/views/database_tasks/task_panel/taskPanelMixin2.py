from __future__ import annotations

from skyadmin_pro.config import TASK_STATUS_COMPLETED, TASK_STATUS_PENDING


class TaskPanelMixin2:
    def _save(self) -> None:
        title = self.title_var.get().strip()
        if not title:
            self.feedback.error("Enter a task title.")
            return
        try:
            due = self._due_date()
            client_id = self._client_id()
            notes = self.notes_field.get()
            if self._editing_id is None:
                task_id = self.app.db.add_task(
                    title=title,
                    client_id=client_id,
                    description=notes,
                    category=self.category_menu.get(),
                    due_date=due,
                )
                self._editing_id = task_id
                self.feedback.success("Task added.")
            else:
                self.app.db.update_task(
                    self._editing_id,
                    title=title,
                    client_id=client_id,
                    description=notes,
                    category=self.category_menu.get(),
                    due_date=due,
                )
                self.feedback.success("Task updated.")
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        except Exception as exc:
            self.feedback.error(f"Could not save task: {exc}")
            return
        saved_status = "pending"
        if self._editing_id is not None:
            try:
                task = self.app.db.get_task(self._editing_id)
                if task:
                    saved_status = task.get("status") or "pending"
            except Exception as e:
                import logging

                logging.error(f"UI Error: {e}")
        self.status_label.configure(text=f"Status: {saved_status}")
        self.refresh()
        if self._editing_id is not None:
            try:
                self.tree.tree.selection_set(str(self._editing_id))
            except Exception as e:
                import logging

                logging.error(f"UI Error: {e}")
        self.app.set_status("Tasks saved.")
        self.app.invalidate_dashboard()

    def _complete(self) -> None:
        if self._editing_id is None:
            self.feedback.error("Select or save a task first.")
            return
        try:
            self.app.db.set_task_status(self._editing_id, TASK_STATUS_COMPLETED)
        except Exception as exc:
            self.feedback.error(f"Could not complete task: {exc}")
            return
        self.feedback.success("Marked as completed.")
        self.refresh()
        self.status_label.configure(text="Status: completed")
        self.app.invalidate_dashboard()

    def _reopen(self) -> None:
        if self._editing_id is None:
            self.feedback.error("Select a task first.")
            return
        try:
            self.app.db.set_task_status(self._editing_id, TASK_STATUS_PENDING)
        except Exception as exc:
            self.feedback.error(f"Could not reopen task: {exc}")
            return
        self.feedback.success("Task reopened.")
        self.refresh()
        self.status_label.configure(text="Status: pending")
        self.app.invalidate_dashboard()
