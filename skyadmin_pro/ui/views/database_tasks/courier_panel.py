"""Courier tracker tab — outgoing delivery log."""

from __future__ import annotations

from datetime import date
from tkinter import messagebox

import customtkinter as ctk

from skyadmin_pro.config import COURIER_DRIVERS, TASK_STATUS_PENDING
from skyadmin_pro.services.file_ops import parse_flexible_date
from skyadmin_pro.ui.combo_utils import fill_combo
from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, FORM_ROW_GAP, FORM_SIDEBAR_MIN_WIDTH
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import FeedbackLabel, FormField, themed_scrollable_frame

from skyadmin_pro.ui.views.database_tasks.constants import NONE_TASK

FORM_PADX = 16


class CourierPanel(ctk.CTkFrame):
    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=FORM_SIDEBAR_MIN_WIDTH)
        self.grid_rowconfigure(0, weight=1)

        tree_card = ctk.CTkFrame(self, corner_radius=CARD_RADIUS)
        tree_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tree_card.grid_columnconfigure(0, weight=1)
        tree_card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            tree_card,
            text="Courier deliveries",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))
        self.tree = ThemedTreeview(
            tree_card,
            columns=(
                ("sent", "Date sent", 110),
                ("client", "Client", 140),
                ("tracking", "Tracking no.", 160),
                ("driver", "Driver", 110),
                ("destination", "Destination", 160),
                ("task", "Related task", 160),
            ),
        )
        self.tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        form = themed_scrollable_frame(self, corner_radius=12, width=FORM_SIDEBAR_MIN_WIDTH)
        form.grid(row=0, column=1, sticky="nsew")
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="Log outgoing delivery", font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=FORM_PADX, pady=(14, 8)
        )

        row = 1
        self.client_field = FormField(form, label="Client", kind="combo", values=[""])
        self.client_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        self.client_box = self.client_field.widget
        row += 1

        self.tracking_var = ctk.StringVar()
        self.tracking_field = FormField(
            form,
            label="Tracking number",
            kind="entry",
            textvariable=self.tracking_var,
            placeholder_text="Tracking / waybill number",
        )
        self.tracking_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        row += 1

        self.driver_field = FormField(form, label="Driver (Grab / Lalamove)", kind="combo", values=list(COURIER_DRIVERS))
        self.driver_field.set("Grab")
        self.driver_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        self.driver_box = self.driver_field.widget
        row += 1

        self.sent_var = ctk.StringVar(value=date.today().isoformat())
        self.sent_field = FormField(form, label="Date sent", kind="date", textvariable=self.sent_var)
        self.sent_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        row += 1

        self.dest_var = ctk.StringVar()
        self.dest_field = FormField(
            form,
            label="Destination",
            kind="entry",
            textvariable=self.dest_var,
            placeholder_text="Delivery address or recipient",
        )
        self.dest_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        row += 1

        self.task_field = FormField(form, label="Related task", kind="option", values=[NONE_TASK])
        self.task_field.set(NONE_TASK)
        self.task_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        self.task_menu = self.task_field.widget
        row += 1

        self.notes_field = FormField(form, label="Notes", kind="textbox", height=70)
        self.notes_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        row += 1

        ctk.CTkButton(form, text="Log delivery", command=self._log).grid(
            row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(14, 6)
        )
        row += 1
        ctk.CTkButton(
            form,
            text="Delete selected",
            fg_color="transparent",
            border_width=1,
            command=self._delete,
        ).grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(0, 14))

        self._task_lookup: dict[str, int] = {}

    def refresh(self) -> None:
        self.tree.apply_theme()
        fill_combo(self.client_box, self.app.db.list_client_names(), self.client_box.get())
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
                notes=self.notes_field.get(),
            )
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success(f"Logged {tracking} ({self.driver_box.get()}).")
        self.tracking_var.set("")
        self.dest_var.set("")
        self.notes_field.clear()
        self.refresh()

    def _delete(self) -> None:
        iid = self.tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a courier log first.")
            return
        if not messagebox.askyesno("Delete courier log", "Remove this delivery record?", parent=self.winfo_toplevel()):
            return
        self.app.db.delete_courier_log(int(iid))
        self.feedback.success("Courier log deleted.")
        self.refresh()
