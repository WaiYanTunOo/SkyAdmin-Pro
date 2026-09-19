from __future__ import annotations

from tkinter import messagebox

from skyadmin_pro.config import MONTHLY_FILING_FIELDS, MONTHLY_TAX_TYPES


class DashboardViewMixin7:
    def _run_monthly_cycle(self) -> None:
        pending = self._count_monthly_cycle_pending()
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

    def _count_monthly_cycle_pending(self) -> int:
        """Pending monthly PND fields (cycle candidates), not dashboard closed+unfinished."""
        placeholders = ",".join("?" for _ in MONTHLY_TAX_TYPES)
        cols = ", ".join(MONTHLY_FILING_FIELDS)
        rows = self.app.db._fetch_all(
            f"SELECT {cols} FROM clients WHERE service_type IN ({placeholders})",
            tuple(MONTHLY_TAX_TYPES),
        )
        return sum(1 for row in rows for f in MONTHLY_FILING_FIELDS if row.get(f) == "Pending")

    def _refresh_tax_overview(self, clients=None) -> None:
        label = getattr(self, "tax_count_label", None)
        if label is None:
            return
        clients = self.app.db.list_accounting_clients() if clients is None else clients
        pending = (getattr(self, "_last_snap", None) or {}).get("pending_filings")
        text = f"{len(clients or [])} accounting client(s)"
        if pending is not None:
            text += f" · {pending} need filing (closed month)"
        try:
            label.configure(text=text)
        except Exception:
            pass
