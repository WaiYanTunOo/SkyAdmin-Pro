from __future__ import annotations

from tkinter import messagebox

from skyadmin_pro.config import PIPELINE_MAX_STEP, PIPELINE_STEPS


class ServicePipelinePanelMixin2:
    def _add_item(self) -> None:
        name = self.pipe_client.get().strip()
        service = self.pipe_service.get().strip()
        if not name or not service:
            self.feedback.error("Select a client and a service.")
            return
        if service not in self.app.db.list_service_types():
            self.feedback.error("Pick a service from the list — add new services in Settings.")
            return
        try:
            client_id = self.app.db.get_or_create_client(name)
            self.app.db.add_pipeline_item(client_id=client_id, service=service)
        except Exception as exc:
            self.feedback.error(f"Could not add pipeline item: {exc}")
            return
        self.feedback.success(f"Added {name} — {service} to the pipeline (step 1).")
        # Silent refresh — clear the loading message so it doesn't flash
        self.pipe_tree.apply_theme()
        self._page = 0
        self._silent_refresh()
        self._refresh_tasks_panel()

    def _selected_item_id(self) -> int | None:
        iid = self.pipe_tree.selected_iid()
        if iid is None:
            return None
        return int(iid)

    def _advance_item(self, _iid: str | None = None) -> None:
        item_id = _iid or self.pipe_tree.selected_iid()
        if item_id is None:
            self.feedback.error("Select a pipeline item first.")
            return
        try:
            item = self.app.db.get_pipeline_item(int(item_id))
        except Exception:
            item = None
        if item and int(item["step"]) >= PIPELINE_MAX_STEP:
            self.feedback.info("This item is already completed.")
            return
        try:
            self.app.db.advance_pipeline(int(item_id))
        except Exception as exc:
            self.feedback.error(f"Could not advance pipeline: {exc}")
            return
        self.feedback.success("Pipeline advanced one step.")
        self.refresh()
        self._refresh_tasks_panel()

    def _set_step(self) -> None:
        item_id = self._selected_item_id()
        if item_id is None:
            self.feedback.error("Select a pipeline item first.")
            return
        try:
            step = int(self.step_menu.get().split(".")[0])
        except ValueError:
            step = 1
        if step < 1:
            step = 1
        if step > PIPELINE_MAX_STEP:
            step = PIPELINE_MAX_STEP
        try:
            self.app.db.set_pipeline_step(item_id, step)
        except Exception as exc:
            self.feedback.error(f"Could not set step: {exc}")
            return
        self.feedback.success(f"Step set to {PIPELINE_STEPS[step - 1]}.")
        self.refresh()
        self._refresh_tasks_panel()

    def _delete_item(self) -> None:
        item_id = self._selected_item_id()
        if item_id is None:
            self.feedback.error("Select a pipeline item first.")
            return
        if not messagebox.askyesno(
            "Delete pipeline item",
            "Delete this pipeline item?\n\nIts pipeline tasks will also be removed.",
            parent=self.winfo_toplevel(),
        ):
            return
        try:
            self.app.db.delete_pipeline_item(item_id)
        except Exception as exc:
            self.feedback.error(f"Could not delete pipeline item: {exc}")
            return
        self.feedback.success("Pipeline item deleted.")
        self.refresh()
        self._refresh_tasks_panel()
