from __future__ import annotations

from skyadmin_pro.config import PIPELINE_MAX_STEP, PIPELINE_STEPS
from skyadmin_pro.ui.combo_utils import fill_combo
from skyadmin_pro.ui.widgets import FeedbackLabel


class ServicePipelinePanelMixin0:
    """9-Step Client-to-Supplier pipeline tracker (service engagement lifecycle)."""

    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        pipeline_card = self._ServicePipelinePanel__init__p1(app, feedback)
        controls = self._ServicePipelinePanel__init__p2(pipeline_card)
        self._ServicePipelinePanel__init__p3(controls)

    def refresh(self) -> None:
        from skyadmin_pro.ui.async_ui import run_background

        self.pipe_tree.apply_theme()
        try:
            current_client = self.pipe_client.get()
        except Exception:
            current_client = ""

        self._refresh_seq += 1
        seq = self._refresh_seq
        db = self.app.db
        page, page_size = self._page, self._page_size
        self.feedback.info("Loading pipeline…")

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
            from .select_pending import apply_pending_select

            apply_pending_select(self)
            summary = payload["summary"]
            self.summary.configure(text=f"{summary['total']} engagement(s) tracked — {summary['completed']} completed.")
            self._update_pager(len(shown))
            self.feedback.clear()

        def on_error(msg: str) -> None:
            if seq != self._refresh_seq or not self.winfo_exists():
                return
            self.feedback.error(f"Pipeline failed to load: {msg}")

        run_background(self, work=work, on_success=on_success, on_error=on_error)
