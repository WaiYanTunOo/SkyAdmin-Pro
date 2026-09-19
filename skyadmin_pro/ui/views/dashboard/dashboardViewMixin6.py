from __future__ import annotations

from tkinter import filedialog

from skyadmin_pro.config import NAV_DATABASE_TASKS


class DashboardViewMixin6:
    def _refresh_report(self) -> None:
        from .report_rows import fill_report

        fill_report(self)

    def _export_pdf(self) -> None:
        from pathlib import Path

        from skyadmin_pro.services.reports import default_report_name, write_status_report_pdf
        from skyadmin_pro.ui.async_ui import run_background

        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            defaultextension=".pdf",
            filetypes=[("PDF document", "*.pdf")],
            initialfile=default_report_name(),
            title="Export status report (PDF)",
        )
        if not path:
            return
        self.workflow_feedback.info("Exporting PDF…")

        def work():
            return write_status_report_pdf(self.app.db, Path(path), offload=True)

        def on_success(_result):
            self.workflow_feedback.success(f"PDF report exported: {path}")
            self.app.set_status("Status report exported to PDF.")

        def on_error(msg: str):
            self.workflow_feedback.error(msg)

        run_background(self, work=work, on_success=on_success, on_error=on_error)

    def _export_report(self) -> None:
        year, month = self._selected_report_month()
        rows = self.app.db.list_incentive_services(year, month)
        if not rows:
            self.workflow_feedback.info("No completed services for this month.")
            return
        from skyadmin_pro.services.export import export_monthly_report
        from skyadmin_pro.ui.async_ui import run_background

        default_name = f"SkyAdmin_Export_{year}{month:02d}01.xlsx"
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx")],
            initialfile=default_name,
            title="Export monthly service report",
        )
        if not path:
            return
        self.workflow_feedback.info("Exporting…")

        def work():
            from pathlib import Path

            return export_monthly_report(self.app.db, year, month, Path(path), offload=True)

        def on_success(_result):
            self.workflow_feedback.success(f"Report exported: {path}")

        def on_error(msg: str):
            self.workflow_feedback.error(msg)

        run_background(self, work=work, on_success=on_success, on_error=on_error)

    def _open_accounting_setup(self) -> None:
        from skyadmin_pro.config import NAV_ACCOUNTING

        open_setup = getattr(self.app, "open_accounting_setup", None)
        if callable(open_setup):
            open_setup()
        else:
            self.app.show_view(NAV_ACCOUNTING)

    def _open_vo_csh_setup(self) -> None:
        open_setup = getattr(self.app, "open_vo_csh_setup", None)
        if callable(open_setup):
            open_setup()
        else:
            self.app.show_view(NAV_DATABASE_TASKS)
