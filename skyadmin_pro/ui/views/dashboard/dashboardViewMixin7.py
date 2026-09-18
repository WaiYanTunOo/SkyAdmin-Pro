from __future__ import annotations

from tkinter import messagebox


class DashboardViewMixin7:
    def _run_monthly_cycle(self) -> None:
        pending = self.app.db.count_pending_filings()
        if not messagebox.askyesno(
            "Run monthly cycle",
            "This will move every Pending filing to On-Going for monthly-tax "
            f"clients and create tasks.\n\n"
            f"{pending} filing(s) are currently Pending. Continue?",
            parent=self.winfo_toplevel(),
        ):
            return
        result = self.app.db.run_monthly_cycle()
        msg = (
            f"Monthly cycle complete: {result['clients_processed']} client(s) processed, "
            f"{result['tasks_created']} task(s) created, "
            f"{result['fields_updated']} filing(s) moved to On-Going."
        )
        self.workflow_feedback.success(msg)
        self.refresh(force=True)

    def _refresh_tax_overview(self, clients=None) -> None:
        label = getattr(self, "tax_count_label", None)
        if label is None:
            return
        clients = self.app.db.list_accounting_clients() if clients is None else clients
        pending = (getattr(self, "_last_snap", None) or {}).get("pending_filings")
        text = f"{len(clients or [])} accounting client(s)"
        if pending is not None:
            text += f" · {pending} filing(s) pending"
        try:
            label.configure(text=text)
        except Exception:
            pass
