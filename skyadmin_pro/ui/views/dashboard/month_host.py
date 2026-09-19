"""One-line month-close count. refresh() stays for dashboard tests."""

from __future__ import annotations

from datetime import date


class MonthCloseHost:
    def __init__(self, app, label) -> None:
        self.app = app
        self.summary = label

    def refresh(self) -> None:
        today = date.today()
        key = f"{today.year:04d}-{today.month:02d}"
        try:
            clients = self.app.db.list_monthly_tax_clients()
            ids = [int(row["id"]) for row in clients]
            summary = self.app.db.month_close_summary(key, client_ids=ids)
        except Exception:
            return
        # Actionable = Open + In progress (exclude Closed).
        not_closed = int(summary["open"]) + int(summary["in_progress"])
        text = f"{not_closed} not closed ({summary['open']} open · {summary['in_progress']} in progress)"
        try:
            self.summary.configure(text=text)
        except Exception as e:
            import logging

            logging.error(f"UI Error: {e}")
