"""Company Details panel — per-company services, tax, VO/CSH, and documents."""

from __future__ import annotations

from datetime import date, timedelta
from tkinter import messagebox

# Sub-tab names — single source of truth for the tab bar, lazy loader,
# refresh dispatcher, and cross-module callers (database_tasks/view.py).


class CompanyDetailsPanelMixin18:
    def _missing_docs_workflow(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        client = self.company_box.get().strip()
        today = date.today()
        deadline = date(today.year, today.month, 15)
        if today.day > 15:
            next_total = today.year * 12 + today.month
            deadline = date(next_total // 12, next_total % 12 + 1, 15)

        from skyadmin_pro.ui.views.company_details import panel as panel_mod

        overrides = panel_mod.load_snippet_overrides(self.app.db.get_setting)
        template = panel_mod.effective_text("client", "Missing docs — initial request", overrides)
        copied = False
        if template:
            message = (
                template.replace("[Client Contact Name]", client)
                .replace("[Client Company Name]", client)
                .replace("[Month/Year]", today.strftime("%B %Y"))
                .replace("[Deadline Date]", deadline.isoformat())
            )
            try:
                panel_mod.copy_to_clipboard(message, tk_window=self.app)
                copied = True
            except Exception as exc:
                self.feedback.error(f"Could not copy the request email: {exc}")

        db = self.app.db
        if not messagebox.askyesno(
            "Missing docs follow-up",
            f"Create 3 follow-up tasks for {client}?\n\n"
            "• Request email (today)\n• Follow-up email (+2 days)\n• Reminder call (+3 days)",
            parent=self.winfo_toplevel(),
        ):
            return
        db.add_task(
            title=f"Send missing docs request to {client}",
            client_id=client_id,
            category="Accounting",
            due_date=today.isoformat(),
        )
        db.add_task(
            title=f"Follow-up: missing docs email to {client}",
            client_id=client_id,
            category="Accounting",
            due_date=(today + timedelta(days=2)).isoformat(),
        )
        db.add_task(
            title=f"Call re: missing docs for {client}",
            client_id=client_id,
            category="Accounting",
            due_date=(today + timedelta(days=3)).isoformat(),
        )
        self.feedback.success(
            f"3 follow-up tasks created for {client} "
            f"(today, +2d email, +3d call)." + (" Request email copied." if copied else "")
        )
        self.app.set_status(f"Missing-docs follow-up scheduled for {client}.")
        view = self.app.get_view("database_tasks")
        if view is not None and getattr(view, "tasks_panel", None) is not None:
            view.tasks_panel.refresh()
