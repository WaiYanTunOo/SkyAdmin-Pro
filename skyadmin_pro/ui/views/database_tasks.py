"""Database & Tasks: live task table, courier tracker, clients, and Excel export."""

from __future__ import annotations

from datetime import date
from tkinter import filedialog, messagebox

import customtkinter as ctk

from skyadmin_pro.config import (
    COURIER_DRIVERS,
    DOC_TYPE_LICENSE,
    DOC_TYPE_PASSPORT_VISA,
    TASK_CATEGORIES,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_PENDING,
)
from skyadmin_pro.services.export import default_export_name, export_to_excel
from skyadmin_pro.services.file_ops import open_in_file_manager, parse_flexible_date
from skyadmin_pro.services.tracking import classify_expiry, days_until, expiry_label
from skyadmin_pro.services.workflow import create_client_workspace
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.widgets import FeedbackLabel

NONE_TASK = "(none)"


def _fill_combo(combo: ctk.CTkComboBox, values: list[str], current: str = "") -> None:
    combo.configure(values=values or [""])
    combo.set(current)


class DatabaseTasksView(BaseView):
    title = "Database & Tasks"
    subtitle = "Offline SQLite tracking for clients, tasks, courier deliveries, and expiry dates."

    def build(self) -> None:
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(self.body, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        toolbar.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            toolbar,
            text="Export to Excel",
            width=140,
            command=self._export_excel,
        ).grid(row=0, column=0, sticky="w")
        self.feedback = FeedbackLabel(toolbar)
        self.feedback.grid(row=0, column=1, sticky="ew", padx=(12, 0))

        self.tabs = ctk.CTkTabview(self.body, command=self.refresh_all)
        self.tabs.grid(row=1, column=0, sticky="nsew")
        for name in ("Tasks", "Courier Tracker", "Clients & Expiry"):
            self.tabs.add(name)
            tab = self.tabs.tab(name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

        self.tasks_panel = TaskPanel(self.tabs.tab("Tasks"), self.app, self.feedback)
        self.tasks_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.courier_panel = CourierPanel(self.tabs.tab("Courier Tracker"), self.app, self.feedback)
        self.courier_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.clients_panel = ClientsExpiryPanel(
            self.tabs.tab("Clients & Expiry"), self.app, self.feedback
        )
        self.clients_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    def on_show(self) -> None:
        self.refresh_all()

    def refresh_all(self) -> None:
        if not hasattr(self, "tasks_panel"):
            return
        self.tasks_panel.refresh()
        self.courier_panel.refresh()
        self.clients_panel.refresh()

    def _export_excel(self) -> None:
        target = filedialog.asksaveasfilename(
            title="Export database to Excel",
            defaultextension=".xlsx",
            initialfile=default_export_name(),
            initialdir=str(self.app.paths.root),
            filetypes=[("Excel workbook", "*.xlsx")],
        )
        if not target:
            return
        try:
            path = export_to_excel(self.app.db, target)
        except Exception as exc:
            self.feedback.error(f"Export failed: {exc}")
            messagebox.showerror("Export failed", str(exc), parent=self.winfo_toplevel())
            return
        self.feedback.success(f"Exported to {path.name}")
        self.app.set_status(f"Exported database to {path}")


class TaskPanel(ctk.CTkFrame):
    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self._editing_id: int | None = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.filter = ctk.CTkSegmentedButton(
            top,
            values=["Pending", "Completed", "All"],
            command=lambda _v: self.refresh(),
        )
        self.filter.set("Pending")
        self.filter.pack(side="left")

        self.tree = ThemedTreeview(
            self,
            columns=(
                ("client", "Client", 140),
                ("title", "Title", 240),
                ("category", "Category", 120),
                ("status", "Status", 90),
                ("due", "Due date", 100),
                ("completed", "Completed", 130),
            ),
            on_select=self._on_select,
        )
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        form = ctk.CTkFrame(self, corner_radius=12, width=320)
        form.grid(row=1, column=1, sticky="nsew")
        form.grid_propagate(False)
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="Task details", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(14, 8)
        )
        self.status_label = ctk.CTkLabel(form, text="Status: new", text_color=("gray40", "gray70"))
        self.status_label.grid(row=1, column=0, sticky="w", padx=14)

        ctk.CTkLabel(form, text="Client").grid(row=2, column=0, sticky="w", padx=14, pady=(10, 2))
        self.client_box = ctk.CTkComboBox(form, values=[""])
        self.client_box.grid(row=3, column=0, sticky="ew", padx=14)

        ctk.CTkLabel(form, text="Title").grid(row=4, column=0, sticky="w", padx=14, pady=(10, 2))
        self.title_var = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self.title_var).grid(row=5, column=0, sticky="ew", padx=14)

        ctk.CTkLabel(form, text="Category").grid(row=6, column=0, sticky="w", padx=14, pady=(10, 2))
        self.category_menu = ctk.CTkOptionMenu(form, values=list(TASK_CATEGORIES))
        self.category_menu.set("General")
        self.category_menu.grid(row=7, column=0, sticky="w", padx=14)

        ctk.CTkLabel(form, text="Due date").grid(row=8, column=0, sticky="w", padx=14, pady=(10, 2))
        self.due_var = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self.due_var, placeholder_text="YYYY-MM-DD").grid(
            row=9, column=0, sticky="ew", padx=14
        )

        ctk.CTkLabel(form, text="Notes").grid(row=10, column=0, sticky="w", padx=14, pady=(10, 2))
        self.notes = ctk.CTkTextbox(form, height=90)
        self.notes.grid(row=11, column=0, sticky="ew", padx=14)

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=12, column=0, sticky="ew", padx=14, pady=(14, 14))
        buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(buttons, text="New", command=self._new).grid(
            row=0, column=0, sticky="ew", padx=(0, 4), pady=3
        )
        ctk.CTkButton(buttons, text="Save", command=self._save).grid(
            row=0, column=1, sticky="ew", padx=(4, 0), pady=3
        )
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

    def refresh(self) -> None:
        self.tree.apply_theme()
        names = self.app.db.list_client_names()
        current = self.client_box.get()
        _fill_combo(self.client_box, names, current)

        choice = self.filter.get()
        status = None
        if choice == "Pending":
            status = TASK_STATUS_PENDING
        elif choice == "Completed":
            status = TASK_STATUS_COMPLETED
        tasks = self.app.db.list_tasks(status=status)

        rows, iids, tags = [], [], []
        for task in tasks:
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
        self.tree.set_rows(rows, iids=iids, tags=tags)

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
        self.notes.delete("1.0", "end")
        if task.get("description"):
            self.notes.insert("1.0", task["description"])
        self.status_label.configure(text=f"Status: {task.get('status', 'pending')}")

    def _new(self) -> None:
        self._editing_id = None
        self.title_var.set("")
        self.due_var.set("")
        self.notes.delete("1.0", "end")
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
            notes = self.notes.get("1.0", "end").strip()
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
        self.status_label.configure(text="Status: pending")
        self.refresh()
        if self._editing_id is not None:
            try:
                self.tree.tree.selection_set(str(self._editing_id))
            except Exception:
                pass
        self.app.set_status("Tasks saved.")

    def _complete(self) -> None:
        if self._editing_id is None:
            self.feedback.error("Select or save a task first.")
            return
        self.app.db.set_task_status(self._editing_id, TASK_STATUS_COMPLETED)
        self.feedback.success("Marked as completed.")
        self.refresh()
        self.status_label.configure(text="Status: completed")

    def _reopen(self) -> None:
        if self._editing_id is None:
            self.feedback.error("Select a task first.")
            return
        self.app.db.set_task_status(self._editing_id, TASK_STATUS_PENDING)
        self.feedback.success("Task reopened.")
        self.refresh()
        self.status_label.configure(text="Status: pending")

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


class CourierPanel(ctk.CTkFrame):
    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)

        self.tree = ThemedTreeview(
            self,
            columns=(
                ("sent", "Date sent", 110),
                ("client", "Client", 140),
                ("tracking", "Tracking no.", 160),
                ("driver", "Driver", 110),
                ("destination", "Destination", 160),
                ("task", "Related task", 160),
            ),
        )
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        form = ctk.CTkFrame(self, corner_radius=12, width=320)
        form.grid(row=0, column=1, sticky="nsew")
        form.grid_propagate(False)
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            form, text="Log outgoing delivery", font=ctk.CTkFont(size=15, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 8))

        ctk.CTkLabel(form, text="Client").grid(row=1, column=0, sticky="w", padx=14, pady=(4, 2))
        self.client_box = ctk.CTkComboBox(form, values=[""])
        self.client_box.grid(row=2, column=0, sticky="ew", padx=14)

        ctk.CTkLabel(form, text="Tracking number").grid(
            row=3, column=0, sticky="w", padx=14, pady=(10, 2)
        )
        self.tracking_var = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self.tracking_var).grid(
            row=4, column=0, sticky="ew", padx=14
        )

        ctk.CTkLabel(form, text="Driver (Grab / Lalamove)").grid(
            row=5, column=0, sticky="w", padx=14, pady=(10, 2)
        )
        self.driver_box = ctk.CTkComboBox(form, values=list(COURIER_DRIVERS))
        self.driver_box.set("Grab")
        self.driver_box.grid(row=6, column=0, sticky="ew", padx=14)

        ctk.CTkLabel(form, text="Date sent").grid(row=7, column=0, sticky="w", padx=14, pady=(10, 2))
        self.sent_var = ctk.StringVar(value=date.today().isoformat())
        ctk.CTkEntry(form, textvariable=self.sent_var, placeholder_text="YYYY-MM-DD").grid(
            row=8, column=0, sticky="ew", padx=14
        )

        ctk.CTkLabel(form, text="Destination").grid(
            row=9, column=0, sticky="w", padx=14, pady=(10, 2)
        )
        self.dest_var = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self.dest_var).grid(row=10, column=0, sticky="ew", padx=14)

        ctk.CTkLabel(form, text="Related task").grid(
            row=11, column=0, sticky="w", padx=14, pady=(10, 2)
        )
        self.task_menu = ctk.CTkOptionMenu(form, values=[NONE_TASK])
        self.task_menu.set(NONE_TASK)
        self.task_menu.grid(row=12, column=0, sticky="ew", padx=14)

        ctk.CTkLabel(form, text="Notes").grid(row=13, column=0, sticky="w", padx=14, pady=(10, 2))
        self.notes = ctk.CTkTextbox(form, height=70)
        self.notes.grid(row=14, column=0, sticky="ew", padx=14)

        ctk.CTkButton(form, text="Log delivery", command=self._log).grid(
            row=15, column=0, sticky="ew", padx=14, pady=(14, 6)
        )
        ctk.CTkButton(
            form,
            text="Delete selected",
            fg_color="transparent",
            border_width=1,
            command=self._delete,
        ).grid(row=16, column=0, sticky="ew", padx=14, pady=(0, 14))

        self._task_lookup: dict[str, int] = {}

    def refresh(self) -> None:
        self.tree.apply_theme()
        _fill_combo(self.client_box, self.app.db.list_client_names(), self.client_box.get())
        pending = self.app.db.list_tasks(status=TASK_STATUS_PENDING)
        self._task_lookup = {f"#{item['id']}  {item['title']}": int(item["id"]) for item in pending}
        values = [NONE_TASK, *self._task_lookup.keys()]
        current = self.task_menu.get()
        self.task_menu.configure(values=values)
        self.task_menu.set(current if current in values else NONE_TASK)

        logs = self.app.db.list_courier_logs()
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
        )

    def _log(self) -> None:
        tracking = self.tracking_var.get().strip()
        if not tracking:
            self.feedback.error("Enter a tracking number.")
            return
        sent = parse_flexible_date(self.sent_var.get())
        if not sent:
            self.feedback.error("Enter a valid date sent.")
            return
        client_name = self.client_box.get().strip()
        client_id = self.app.db.get_or_create_client(client_name) if client_name else None
        task_choice = self.task_menu.get()
        task_id = self._task_lookup.get(task_choice)
        try:
            self.app.db.add_courier_log(
                tracking_number=tracking,
                driver_name=self.driver_box.get(),
                date_sent=sent,
                client_id=client_id,
                task_id=task_id,
                destination=self.dest_var.get(),
                notes=self.notes.get("1.0", "end").strip(),
            )
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success(f"Logged {tracking} ({self.driver_box.get()}).")
        self.tracking_var.set("")
        self.dest_var.set("")
        self.notes.delete("1.0", "end")
        self.refresh()

    def _delete(self) -> None:
        iid = self.tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a courier log first.")
            return
        if not messagebox.askyesno(
            "Delete courier log", "Remove this delivery record?", parent=self.winfo_toplevel()
        ):
            return
        self.app.db.delete_courier_log(int(iid))
        self.feedback.success("Courier log deleted.")
        self.refresh()


class ClientsExpiryPanel(ctk.CTkFrame):
    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(self, corner_radius=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(left, text="Clients", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(14, 8)
        )
        self.client_tree = ThemedTreeview(
            left,
            columns=(("name", "Client name", 220), ("created", "Added", 140)),
        )
        self.client_tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        add_row = ctk.CTkFrame(left, fg_color="transparent")
        add_row.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 14))
        add_row.grid_columnconfigure(0, weight=1)
        self.new_client_var = ctk.StringVar()
        ctk.CTkEntry(add_row, textvariable=self.new_client_var, placeholder_text="New client name").grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ctk.CTkButton(add_row, text="Add", width=70, command=self._add_client).grid(row=0, column=1)
        ctk.CTkButton(
            add_row,
            text="Generate Workspace",
            width=160,
            command=self._generate_workspace,
        ).grid(row=0, column=2, padx=(8, 0))
        ctk.CTkButton(
            add_row,
            text="Delete",
            width=70,
            fg_color="transparent",
            border_width=1,
            command=self._delete_client,
        ).grid(row=0, column=3, padx=(8, 0))

        right = ctk.CTkFrame(self, corner_radius=12)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(6, weight=1)
        ctk.CTkLabel(
            right, text="Register passport / license expiry", font=ctk.CTkFont(size=15, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 8))

        form = ctk.CTkFrame(right, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew", padx=14)
        form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(form, text="Client").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.expiry_client = ctk.CTkComboBox(form, values=[""])
        self.expiry_client.grid(row=0, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(form, text="Type").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.expiry_type = ctk.CTkOptionMenu(
            form, values=[DOC_TYPE_PASSPORT_VISA, DOC_TYPE_LICENSE]
        )
        self.expiry_type.set(DOC_TYPE_PASSPORT_VISA)
        self.expiry_type.grid(row=1, column=1, sticky="w", pady=4)
        ctk.CTkLabel(form, text="Expiry").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        self.expiry_var = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self.expiry_var, placeholder_text="YYYY-MM-DD").grid(
            row=2, column=1, sticky="ew", pady=4
        )
        ctk.CTkButton(right, text="Save expiry record", command=self._add_expiry).grid(
            row=2, column=0, sticky="ew", padx=14, pady=(10, 8)
        )

        self.doc_tree = ThemedTreeview(
            right,
            columns=(
                ("client", "Client", 140),
                ("type", "Type", 120),
                ("expiry", "Expiry", 100),
                ("status", "Status", 140),
            ),
        )
        self.doc_tree.grid(row=6, column=0, sticky="nsew", padx=12, pady=(0, 8))
        ctk.CTkButton(
            right,
            text="Delete selected record",
            fg_color="transparent",
            border_width=1,
            command=self._delete_document,
        ).grid(row=7, column=0, sticky="w", padx=14, pady=(0, 14))

    def refresh(self) -> None:
        self.client_tree.apply_theme()
        self.doc_tree.apply_theme()
        clients = self.app.db.list_clients()
        self.client_tree.set_rows(
            [(item["name"], (item.get("created_at") or "")[:10]) for item in clients],
            iids=[str(item["id"]) for item in clients],
        )
        names = [item["name"] for item in clients]
        _fill_combo(self.expiry_client, names, self.expiry_client.get())

        documents = [item for item in self.app.db.list_documents() if item.get("expiry_date")]
        rows, iids, tags = [], [], []
        for item in documents:
            left = days_until(item.get("expiry_date"))
            status = expiry_label(left) if left is not None else "—"
            tag = classify_expiry(left) if left is not None else "odd"
            rows.append(
                (
                    item.get("client_name") or "—",
                    item.get("document_type") or "—",
                    item.get("expiry_date") or "—",
                    status,
                )
            )
            iids.append(str(item["id"]))
            tags.append((tag,) if left is not None else ())
        self.doc_tree.set_rows(rows, iids=iids, tags=tags)

    def _add_client(self) -> None:
        name = self.new_client_var.get().strip()
        if not name:
            self.feedback.error("Enter a client name.")
            return
        self.app.db.get_or_create_client(name)
        self.new_client_var.set("")
        self.feedback.success(f"Client saved: {name}")
        self.refresh()

    def _generate_workspace(self) -> None:
        name = self.new_client_var.get().strip()
        if not name:
            selected = self.client_tree.selected_values()
            name = selected[0] if selected else ""
        if not name:
            self.feedback.error("Enter a new client name, or select an existing client.")
            return
        try:
            self.app.db.get_or_create_client(name)
            folder = create_client_workspace(self.app.paths.clients, name)
        except Exception as exc:
            self.feedback.error(str(exc))
            return
        self.new_client_var.set("")
        self.feedback.success(
            f"Workspace ready: {folder.name}/01_Company_Setup, 02_Accounting, 03_Visa"
        )
        self.refresh()
        try:
            open_in_file_manager(folder)
        except Exception as exc:
            self.feedback.info(str(exc))

    def _delete_client(self) -> None:
        iid = self.client_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a client first.")
            return
        if not messagebox.askyesno(
            "Delete client",
            "Delete this client? Tasks and documents stay, but the client name is cleared.",
            parent=self.winfo_toplevel(),
        ):
            return
        self.app.db.delete_client(int(iid))
        self.feedback.success("Client deleted.")
        self.refresh()

    def _add_expiry(self) -> None:
        client = self.expiry_client.get().strip()
        if not client:
            self.feedback.error("Choose or type a client name.")
            return
        expiry = parse_flexible_date(self.expiry_var.get())
        if not expiry:
            self.feedback.error("Enter a valid expiry date.")
            return
        client_id = self.app.db.get_or_create_client(client)
        self.app.db.record_document(
            client_id=client_id,
            document_type=self.expiry_type.get(),
            file_name="",
            file_path="",
            expiry_date=expiry,
        )
        self.feedback.success(f"Expiry recorded for {client} ({expiry}).")
        self.expiry_var.set("")
        self.refresh()

    def _delete_document(self) -> None:
        iid = self.doc_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select an expiry record first.")
            return
        self.app.db.delete_document(int(iid))
        self.feedback.success("Expiry record deleted.")
        self.refresh()
