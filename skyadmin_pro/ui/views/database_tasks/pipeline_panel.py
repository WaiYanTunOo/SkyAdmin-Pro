"""Service pipeline tab — 9-step client engagement tracker."""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from skyadmin_pro.config import PIPELINE_MAX_STEP, PIPELINE_STEPS
from skyadmin_pro.ui.combo_utils import fill_combo
from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import FeedbackLabel, bind_wrap_label, combo_style_kwargs


class ServicePipelinePanel(ctk.CTkFrame):
    """9-Step Client-to-Supplier pipeline tracker (service engagement lifecycle)."""

    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.grid_columnconfigure(1, weight=1)
        top.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(top, text="Client:", anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.pipe_client = ctk.CTkComboBox(top, values=[""], **combo_style_kwargs())
        self.pipe_client.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        ctk.CTkLabel(top, text="Service:", anchor="w").grid(row=0, column=2, sticky="w", padx=(0, 8))
        self.pipe_service = ctk.CTkComboBox(
            top, values=self.app.db.list_service_types(), state="readonly", **combo_style_kwargs()
        )
        self.pipe_service.grid(row=0, column=3, sticky="ew", padx=(0, 12))
        ctk.CTkButton(top, text="Add to pipeline", width=130, command=self._add_item).grid(row=0, column=4)

        pipeline_card = ctk.CTkFrame(self, corner_radius=CARD_RADIUS)
        pipeline_card.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        pipeline_card.grid_columnconfigure(0, weight=1)
        pipeline_card.grid_rowconfigure(2, weight=1)
        title_row = ctk.CTkFrame(pipeline_card, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        title_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            title_row,
            text="Service pipeline",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        self.summary = ctk.CTkLabel(title_row, text="", text_color=TEXT_MUTED, anchor="e")
        self.summary.grid(row=0, column=1, sticky="e", padx=(12, 0))

        self.pipe_tree = ThemedTreeview(
            pipeline_card,
            columns=(
                ("client", "Client", 170),
                ("service", "Service", 220),
                ("step", "Step", 70),
                ("status", "Status", 260),
                ("updated", "Updated", 120),
            ),
            on_double_click=self._advance_item,
            table_id="pipeline",
            db=self.app.db,
        )
        self.pipe_tree.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew")
        controls.grid_columnconfigure(4, weight=1)
        ctk.CTkLabel(controls, text="Set step:").grid(row=0, column=0, sticky="w")
        self.step_menu = ctk.CTkOptionMenu(
            controls,
            values=list(PIPELINE_STEPS),
        )
        self.step_menu.set(PIPELINE_STEPS[0])
        self.step_menu.grid(row=0, column=1, sticky="w", padx=(4, 8))
        ctk.CTkButton(controls, text="Apply", width=70, command=self._set_step).grid(row=0, column=2)
        ctk.CTkButton(controls, text="Advance step", width=120, command=self._advance_item).grid(
            row=0, column=3, padx=(8, 0)
        )
        ctk.CTkButton(
            controls,
            text="Delete",
            width=70,
            fg_color="transparent",
            border_width=1,
            command=self._delete_item,
        ).grid(row=0, column=5, padx=(8, 0))
        hint = ctk.CTkLabel(
            controls,
            text="Double-click a row to advance. Steps 3 and 7 are the money milestones.",
            text_color=TEXT_MUTED,
            anchor="e",
            justify="right",
        )
        hint.grid(row=1, column=0, columnspan=6, sticky="ew", pady=(6, 0))
        bind_wrap_label(hint, controls, pad=16)

    def refresh(self) -> None:
        self.pipe_tree.apply_theme()
        fill_combo(self.pipe_client, self.app.db.list_client_names(), self.pipe_client.get())
        self.pipe_service.configure(values=self.app.db.list_service_types())
        items = self.app.db.list_pipeline_items()
        rows: list[tuple] = []
        iids: list[str] = []
        tags: list[list[str]] = []
        for item in items:
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
        summary = self.app.db.pipeline_summary()
        self.summary.configure(text=f"{summary['total']} engagement(s) tracked — {summary['completed']} completed.")

    def _refresh_tasks_panel(self) -> None:
        view = self.app.get_view("database_tasks")
        if view is not None and getattr(view, "tasks_panel", None) is not None:
            view.tasks_panel.refresh()

    def _add_item(self) -> None:
        name = self.pipe_client.get().strip()
        service = self.pipe_service.get().strip()
        if not name or not service:
            self.feedback.error("Select a client and a service.")
            return
        if service not in self.app.db.list_service_types():
            self.feedback.error("Pick a service from the list — add new services in Settings.")
            return
        client_id = self.app.db.get_or_create_client(name)
        self.app.db.add_pipeline_item(client_id=client_id, service=service)
        self.pipe_service.set("")
        self.feedback.success(f"Added {name} — {service} to the pipeline (step 1).")
        self.refresh()
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
        item = self.app.db.get_pipeline_item(int(item_id))
        if item and int(item["step"]) >= PIPELINE_MAX_STEP:
            self.feedback.info("This item is already completed.")
            return
        self.app.db.advance_pipeline(int(item_id))
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
        self.app.db.set_pipeline_step(item_id, step)
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
        self.app.db.delete_pipeline_item(item_id)
        self.feedback.success("Pipeline item deleted.")
        self.refresh()
        self._refresh_tasks_panel()
