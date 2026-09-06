"""Tasks tab — pending/completed task list and editor."""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from skyadmin_pro.config import (
    TASK_CATEGORIES,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_PENDING,
)
from skyadmin_pro.services.file_ops import parse_flexible_date
from skyadmin_pro.ui.combo_utils import fill_combo
from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, FORM_ROW_GAP, FORM_SIDEBAR_MIN_WIDTH, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import FeedbackLabel, FormField, themed_scrollable_frame

FORM_PADX = 16


class TaskPanel(ctk.CTkFrame):
    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self._editing_id: int | None = None
        self._refresh_seq = 0
        self._page = 0
        self._page_size = 250
        self._has_more = False
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=FORM_SIDEBAR_MIN_WIDTH)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.filter = ctk.CTkSegmentedButton(
            top,
            values=["Pending", "Completed", "All"],
            command=lambda _v: (setattr(self, "_page", 0), self.refresh()),
        )
        self.filter.set("Pending")
        self.filter.pack(side="left")
        self.columns_btn = ctk.CTkButton(
            top,
            text="⋮ Columns",
            width=90,
            fg_color="transparent",
            border_width=1,
            command=self._show_columns_menu,
        )
        self.columns_btn.pack(side="right")

        tree_card = ctk.CTkFrame(self, corner_radius=CARD_RADIUS)
        tree_card.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        tree_card.grid_columnconfigure(0, weight=1)
        tree_card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            tree_card,
            text="Tasks",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))
        self.tree = ThemedTreeview(
            tree_card,
            columns=(
                ("client", "Client", 140),
                ("title", "Title", 240),
                ("category", "Category", 120),
                ("status", "Status", 90),
                ("due", "Due date", 100),
                ("completed", "Completed", 130),
            ),
            on_select=self._on_select,
            table_id="tasks",
            db=self.app.db,
        )
        self.tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 4))

        pager = ctk.CTkFrame(tree_card, fg_color="transparent")
        pager.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
        self.prev_btn = ctk.CTkButton(
            pager,
            text="◀ Prev",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=self._prev_page,
        )
        self.prev_btn.pack(side="left")
        self.page_label = ctk.CTkLabel(pager, text="Page 1", text_color=TEXT_MUTED)
        self.page_label.pack(side="left", padx=10)
        self.next_btn = ctk.CTkButton(
            pager,
            text="Next ▶",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=self._next_page,
        )
        self.next_btn.pack(side="left")
        self.page_size_menu = ctk.CTkOptionMenu(
            pager,
            values=["100", "250", "500", "1000"],
            width=90,
            command=self._on_page_size,
        )
        self.page_size_menu.set("250")
        self.page_size_menu.pack(side="right")

        form = themed_scrollable_frame(self, corner_radius=12, width=FORM_SIDEBAR_MIN_WIDTH)
        form.grid(row=1, column=1, sticky="nsew")
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="Task details", font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=FORM_PADX, pady=(14, 8)
        )
        self.status_label = ctk.CTkLabel(form, text="Status: new", text_color=TEXT_MUTED)
        self.status_label.grid(row=1, column=0, sticky="w", padx=FORM_PADX)

        row = 2
        self.client_field = FormField(form, label="Client", kind="combo", values=[""])
        self.client_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        self.client_box = self.client_field.widget
        row += 1

        self.title_var = ctk.StringVar()
        self.title_field = FormField(
            form,
            label="Title",
            kind="entry",
            textvariable=self.title_var,
            placeholder_text="Task title",
        )
        self.title_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        row += 1

        self.category_field = FormField(form, label="Category", kind="option", values=list(TASK_CATEGORIES))
        self.category_field.set("General")
        self.category_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        self.category_menu = self.category_field.widget
        row += 1

        self.due_var = ctk.StringVar()
        self.due_field = FormField(form, label="Due date", kind="date", textvariable=self.due_var)
        self.due_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        row += 1

        self.notes_field = FormField(form, label="Notes", kind="textbox", height=90)
        self.notes_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        self.notes = self.notes_field.widget
        row += 1

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(14, 14))
        buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(buttons, text="New", command=self._new).grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=3)
        ctk.CTkButton(buttons, text="Save", command=self._save).grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=3)
        ctk.CTkButton(buttons, text="Mark complete", command=self._complete).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=3
        )
        ctk.CTkButton(
            buttons,
            text="Reopen",
            fg_color="transparent",
            border_width=1,
            command=self._reopen,
        ).grid(row=2, column=0, sticky="ew", padx=(0, 4), pady=3)
        ctk.CTkButton(
            buttons,
            text="Delete",
            fg_color="transparent",
            border_width=1,
            command=self._delete,
        ).grid(row=2, column=1, sticky="ew", padx=(4, 0), pady=3)

    def _show_columns_menu(self) -> None:
        try:
            x = self.columns_btn.winfo_rootx()
            y = self.columns_btn.winfo_rooty() + self.columns_btn.winfo_height()
        except Exception:
            return
        self.tree.show_column_menu(x, y)

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

        self._refresh_seq += 1
        seq = self._refresh_seq
        db = self.app.db
        page, page_size = self._page, self._page_size
        self.feedback.info("Loading tasks…")

        def work():
            names = db.list_client_names()
            # Fetch one extra row to know whether a next page exists.
            tasks = db.list_tasks(status=status, limit=page_size + 1, offset=page * page_size)
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
        saved_status = "pending"
        if self._editing_id is not None:
            task = self.app.db.get_task(self._editing_id)
            if task:
                saved_status = task.get("status") or "pending"
        self.status_label.configure(text=f"Status: {saved_status}")
        self.refresh()
        if self._editing_id is not None:
            try:
                self.tree.tree.selection_set(str(self._editing_id))
            except Exception:
                pass
        self.app.set_status("Tasks saved.")
        self.app.invalidate_dashboard()

    def _complete(self) -> None:
        if self._editing_id is None:
            self.feedback.error("Select or save a task first.")
            return
        self.app.db.set_task_status(self._editing_id, TASK_STATUS_COMPLETED)
        self.feedback.success("Marked as completed.")
        self.refresh()
        self.status_label.configure(text="Status: completed")
        self.app.invalidate_dashboard()

    def _reopen(self) -> None:
        if self._editing_id is None:
            self.feedback.error("Select a task first.")
            return
        self.app.db.set_task_status(self._editing_id, TASK_STATUS_PENDING)
        self.feedback.success("Task reopened.")
        self.refresh()
        self.status_label.configure(text="Status: pending")
        self.app.invalidate_dashboard()

    def _delete(self) -> None:
        if self._editing_id is None:
            self.feedback.error("Select a task first.")
            return
        if not messagebox.askyesno(
            "Delete task",
            "Delete this task? Courier logs linked to it will be kept.",
            parent=self.winfo_toplevel(),
        ):
            return
        self.app.db.delete_task(self._editing_id)
        self.feedback.success("Task deleted.")
        self._new()
        self.refresh()
        self.app.invalidate_dashboard()
