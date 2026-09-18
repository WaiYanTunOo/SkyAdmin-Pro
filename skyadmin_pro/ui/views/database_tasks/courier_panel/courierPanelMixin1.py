from __future__ import annotations

from tkinter import messagebox

from skyadmin_pro.services.file_ops import parse_flexible_date


class CourierPanelMixin1:
    def _on_page_size(self, value: str) -> None:
        try:
            self._page_size = max(50, int(value))
        except ValueError:
            self._page_size = 250
        self._page = 0
        self.refresh()

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
        try:
            client_id = self.app.db.get_or_create_client(client_name) if client_name else None
        except Exception as exc:
            self.feedback.error(f"Could not resolve client: {exc}")
            return
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
        except Exception as exc:
            self.feedback.error(f"Could not log courier: {exc}")
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
        try:
            self.app.db.delete_courier_log(int(iid))
        except Exception as exc:
            self.feedback.error(f"Could not delete log: {exc}")
            return
        self.feedback.success("Courier log deleted.")
        self.refresh()
