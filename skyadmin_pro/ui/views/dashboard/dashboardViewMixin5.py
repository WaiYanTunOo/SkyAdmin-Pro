from __future__ import annotations

from datetime import date

from skyadmin_pro.services.file_ops import open_in_file_manager
from skyadmin_pro.services.workflow import copy_to_clipboard, create_client_workspace, format_eod_report


class DashboardViewMixin5:
    def _copy_overdue_reminder(self) -> None:
        # Orphaned handler (no overdue_tree). Jump card → Suppliers remains.
        self.workflow_feedback.info("Open Suppliers from the Overdue payments card to manage payments.")

    def _mark_overdue_paid(self) -> None:
        self.workflow_feedback.info("Open Suppliers from the Overdue payments card to mark payments paid.")

    def _mark_supplier_due_paid(self) -> None:
        self.workflow_feedback.info("Open Suppliers from the Supplier due card to mark payments paid.")

    def _open_folder(self, folder) -> None:
        try:
            open_in_file_manager(folder)
        except Exception as exc:
            self.workflow_feedback.error(f"Could not open folder:\n{folder}\n{exc}")
            return
        self.app.set_status(f"Opened folder: {folder}")

    def _copy_eod(self) -> None:
        tasks = self.app.db.list_completed_today()
        pipeline = self.app.db.pipeline_completed_today()
        report = format_eod_report(tasks, pipeline=pipeline)
        try:
            copy_to_clipboard(report, tk_window=self.app)
        except Exception as exc:
            self.workflow_feedback.error(str(exc))
            return
        count = len(tasks) + len(pipeline)
        if count:
            self.workflow_feedback.success(f"EOD report copied ({count} item(s)). Paste into chat or email.")
        else:
            self.workflow_feedback.info("Nothing completed today — empty report copied.")
        self.app.set_status("EOD report copied to clipboard.")

    def _generate_workspace(self) -> None:
        name = self.onboard_var.get().strip()
        if not name:
            self.workflow_feedback.error("Enter a new client name.")
            return
        try:
            self.app.db.get_or_create_client(name)
            folder = create_client_workspace(self.app.paths.clients, name)
        except Exception as exc:
            self.workflow_feedback.error(str(exc))
            return
        self.onboard_var.set("")
        self.workflow_feedback.success(f"Workspace ready: {folder.name}/01_Company_Setup, 02_Accounting, 03_Visa")
        self.app.set_status(f"Created client workspace at {folder}")
        self.refresh(force=True)
        try:
            open_in_file_manager(folder)
        except Exception as exc:
            self.workflow_feedback.info(str(exc))

    def _selected_report_month(self) -> tuple[int, int]:
        label = self._report_month_var.get()
        idx = [f"{date(y, m, 1):%b %Y}" for y, m in self._report_months].index(label)
        return self._report_months[idx]
