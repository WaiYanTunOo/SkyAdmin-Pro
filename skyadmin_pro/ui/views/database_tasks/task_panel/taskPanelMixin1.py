from __future__ import annotations

from skyadmin_pro.config import TASK_CATEGORIES
from skyadmin_pro.services.file_ops import parse_flexible_date


class TaskPanelMixin1:
    def _clear_search(self) -> None:
        self.search_var.set("")
        self._run_search()
        try:
            self.search_entry.focus_set()
        except Exception as e:
            import logging

            logging.error(f"UI Error: {e}")

    def _update_pager(self, shown: int) -> None:
        label = f"Page {self._page + 1} · {shown} shown"
        if self._has_more:
            label += " · more…"
        try:
            self.page_label.configure(text=label)
            self.prev_btn.configure(state="normal" if self._page > 0 else "disabled")
            self.next_btn.configure(state="normal" if self._has_more else "disabled")
        except Exception as e:
            import logging

            logging.error(f"UI Error: {e}")

    def _prev_page(self) -> None:
        if self._page > 0:
            self._page -= 1
            self.refresh()

    def _next_page(self) -> None:
        if self._has_more:
            self._page += 1
            self.refresh()

    def _on_page_size(self, value: str) -> None:
        try:
            self._page_size = max(50, int(value))
        except ValueError:
            self._page_size = 250
        self._page = 0
        self.refresh()

    def _on_select(self, iid: str | None) -> None:
        if iid is None:
            return
        task = self.app.db.get_task(int(iid))
        if not task:
            return
        self._editing_id = int(task["id"])
        self.client_box.set(task.get("client_name") or "")
        self.title_var.set(task.get("title") or "")
        category = task.get("category") or "General"
        if category not in TASK_CATEGORIES:
            category = category.title() if category.title() in TASK_CATEGORIES else "General"
        self.category_menu.set(category)
        self.due_var.set(task.get("due_date") or "")
        self.notes_field.set(task.get("description") or "")
        self.status_label.configure(text=f"Status: {task.get('status', 'pending')}")

    def select_task(self, task_id: int) -> None:
        iid = str(task_id)
        if not self.tree.tree.exists(iid):
            self.refresh()
        if self.tree.tree.exists(iid):
            self.tree.tree.selection_set(iid)
            self.tree.tree.see(iid)
            self._on_select(iid)
        else:
            self.feedback.info("That task is not in the current filter.")

    def _new(self) -> None:
        self._editing_id = None
        self.title_var.set("")
        self.due_var.set("")
        self.notes_field.clear()
        self.category_menu.set("General")
        self.client_box.set("")
        self.status_label.configure(text="Status: new")
        self.tree.tree.selection_remove(*self.tree.tree.selection())

    def _client_id(self) -> int | None:
        name = self.client_box.get().strip()
        if not name:
            return None
        return self.app.db.get_or_create_client(name)

    def _due_date(self) -> str | None:
        raw = self.due_var.get().strip()
        if not raw:
            return None
        parsed = parse_flexible_date(raw)
        if not parsed:
            raise ValueError("Enter a valid due date (YYYY-MM-DD or DD/MM/YYYY).")
        return parsed
