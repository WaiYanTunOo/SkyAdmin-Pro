from __future__ import annotations

from skyadmin_pro.config import TASK_STATUS_PENDING
from skyadmin_pro.ui.combo_utils import fill_combo
from skyadmin_pro.ui.views.database_tasks.constants import NONE_TASK
from skyadmin_pro.ui.widgets import FeedbackLabel


class CourierPanelMixin0:
    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        pager = self._CourierPanel__init__p1(app, feedback)
        form, row = self._CourierPanel__init__p2(pager)
        self._CourierPanel__init__p3(form, row)

    def refresh(self) -> None:
        from skyadmin_pro.ui.async_ui import run_background

        self.tree.apply_theme()
        try:
            current_client = self.client_box.get()
        except Exception:
            current_client = ""
        try:
            current_task = self.task_menu.get()
        except Exception:
            current_task = NONE_TASK

        self._refresh_seq += 1
        seq = self._refresh_seq
        db = self.app.db
        page, page_size = self._page, self._page_size
        self.feedback.info("Loading courier deliveries…")

        def work():
            return {
                "names": db.list_client_names(),
                "pending": db.list_tasks(status=TASK_STATUS_PENDING),
                "logs": db.list_courier_logs(limit=page_size + 1, offset=page * page_size),
                "current_client": current_client,
                "current_task": current_task,
            }

        def on_success(payload) -> None:
            if seq != self._refresh_seq or not self.winfo_exists():
                return
            fill_combo(self.client_box, payload["names"], payload["current_client"])
            self._task_lookup = {f"#{item['id']}  {item['title']}": int(item["id"]) for item in payload["pending"]}
            values = [NONE_TASK, *self._task_lookup.keys()]
            cur = payload["current_task"]
            self.task_menu.configure(values=values)
            self.task_menu.set(cur if cur in values else NONE_TASK)
            fetched = payload["logs"]
            self._has_more = len(fetched) > self._page_size
            logs = fetched[: self._page_size]
            self.tree.set_rows(
                [
                    (
                        item.get("date_sent") or "—",
                        item.get("client_name") or "—",
                        item.get("tracking_number") or "",
                        item.get("driver_name") or "—",
                        item.get("destination") or "—",
                        item.get("task_title") or "—",
                    )
                    for item in logs
                ],
                iids=[str(item["id"]) for item in logs],
                empty_message="No courier deliveries yet.",
            )
            self._update_pager(len(logs))
            self.feedback.clear()

        def on_error(msg: str) -> None:
            if seq != self._refresh_seq or not self.winfo_exists():
                return
            self.feedback.error(f"Courier log failed to load: {msg}")

        run_background(self, work=work, on_success=on_success, on_error=on_error)

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
