from __future__ import annotations

from skyadmin_pro.config import PIPELINE_MAX_STEP, PIPELINE_STEPS
from skyadmin_pro.ui.combo_utils import fill_combo


class ServicePipelinePanelMixin1:
    def _silent_refresh(self) -> None:
        """Refresh the pipeline tree without showing the loading feedback message."""
        from skyadmin_pro.ui.async_ui import run_background

        try:
            current_client = self.pipe_client.get()
        except Exception:
            current_client = ""

        self._refresh_seq += 1
        seq = self._refresh_seq
        db = self.app.db
        page, page_size = self._page, self._page_size

        def work():
            return {
                "names": db.list_client_names(),
                "service_types": db.list_service_types(),
                "items": db.list_pipeline_items(limit=page_size + 1, offset=page * page_size),
                "summary": db.pipeline_summary(),
                "current_client": current_client,
            }

        def on_success(payload) -> None:
            if seq != self._refresh_seq or not self.winfo_exists():
                return
            fill_combo(self.pipe_client, payload["names"], payload["current_client"])
            self.pipe_service.configure(values=payload["service_types"])
            fetched = payload["items"]
            self._has_more = len(fetched) > self._page_size
            shown = fetched[: self._page_size]
            rows: list[tuple] = []
            iids: list[str] = []
            tags: list[list[str]] = []
            for item in shown:
                step = max(1, min(int(item["step"]), PIPELINE_MAX_STEP))
                status = PIPELINE_STEPS[step - 1]
                tag = "done" if step == PIPELINE_MAX_STEP else ("wip" if step in (4, 5, 6, 7, 8) else "")
                rows.append(
                    (
                        item.get("client_name") or "Unassigned",
                        item["service"],
                        f"{step}/{PIPELINE_MAX_STEP}",
                        status,
                        item.get("updated_at") or "",
                    )
                )
                iids.append(str(item["id"]))
                tags.append([tag] if tag else [])
            self.pipe_tree.set_rows(rows, iids=iids, tags=tags, empty_message="No pipeline items yet.")
            summary = payload["summary"]
            self.summary.configure(text=f"{summary['total']} engagement(s) tracked — {summary['completed']} completed.")
            self._update_pager(len(shown))

        def on_error(msg: str) -> None:
            pass  # silently ignore errors on silent refresh

        run_background(self, work=work, on_success=on_success, on_error=on_error)

    def _update_pager(self, shown: int) -> None:
        label = f"Page {self._page + 1} · {shown} shown"
        if self._has_more:
            label += " · more…"
        try:
            self.page_label.configure(text=label)
            self.prev_btn.configure(state="normal" if self._page > 0 else "disabled")
            self.next_btn.configure(state="normal" if self._has_more else "disabled")
        except Exception:
            pass

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

    def _refresh_tasks_panel(self) -> None:
        view = self.app.get_view("tasks")
        panel = getattr(view, "panel", None) if view is not None else None
        if panel is not None and hasattr(panel, "refresh"):
            panel.refresh()
