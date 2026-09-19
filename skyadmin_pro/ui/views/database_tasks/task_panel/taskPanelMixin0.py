from __future__ import annotations

from skyadmin_pro.config import TASK_STATUS_COMPLETED, TASK_STATUS_PENDING
from skyadmin_pro.ui.combo_utils import fill_combo
from skyadmin_pro.ui.widgets import FeedbackLabel


class TaskPanelMixin0:
    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        top = self._TaskPanel__init__p1(app, feedback)
        pager = self._TaskPanel__init__p2(top)
        form, row = self._TaskPanel__init__p3(pager)
        self._TaskPanel__init__p4(form, row)

    def refresh(self) -> None:
        """Non-blocking refresh: DB work off the Tk thread, Treeview on it."""
        from skyadmin_pro.ui.async_ui import run_background

        self.tree.apply_theme()
        try:
            choice = self.filter.get()
        except Exception:
            choice = "Pending"
        try:
            current_combo = self.client_box.get()
        except Exception:
            current_combo = ""
        status = None
        if choice == "Pending":
            status = TASK_STATUS_PENDING
        elif choice == "Completed":
            status = TASK_STATUS_COMPLETED

        try:
            search_query = self.search_var.get().strip()
        except Exception:
            search_query = ""

        self._refresh_seq += 1
        seq = self._refresh_seq
        db = self.app.db
        page, page_size = self._page, self._page_size
        self.feedback.info("Loading tasks…")

        def work():
            names = db.list_client_names()
            # Fetch one extra row to know whether a next page exists.
            tasks = db.list_tasks(status=status, q=search_query, limit=page_size + 1, offset=page * page_size)
            return {"names": names, "tasks": tasks, "choice": choice, "current": current_combo}

        def on_success(payload) -> None:
            if seq != self._refresh_seq or not self.winfo_exists():
                return
            fill_combo(self.client_box, payload["names"], payload["current"])
            fetched = payload["tasks"]
            self._has_more = len(fetched) > self._page_size
            shown = fetched[: self._page_size]
            rows, iids, tags = [], [], []
            for task in shown:
                rows.append(
                    (
                        task.get("client_name") or "—",
                        task.get("title") or "",
                        task.get("category") or "",
                        (task.get("status") or "").title(),
                        task.get("due_date") or "—",
                        (task.get("completed_at") or "—")[:16],
                    )
                )
                iids.append(str(task["id"]))
                tags.append(("completed",) if task.get("status") == TASK_STATUS_COMPLETED else ())
            self.tree.set_rows(rows, iids=iids, tags=tags, empty_message="No tasks in this view.")
            self._update_pager(len(shown))
            self.feedback.clear()

        def on_error(msg: str) -> None:
            if seq != self._refresh_seq or not self.winfo_exists():
                return
            self.feedback.error(f"Tasks failed to load: {msg}")

        run_background(self, work=work, on_success=on_success, on_error=on_error)

    def _debounced_search(self) -> None:
        if self._search_after is not None:
            try:
                self.after_cancel(self._search_after)
            except Exception:
                pass
        self._search_after = self.after(300, self._run_search)

    def _run_search(self) -> None:
        self._search_after = None
        self._page = 0
        self.refresh()
