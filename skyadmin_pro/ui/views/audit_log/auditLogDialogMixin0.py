from __future__ import annotations


class AuditLogDialogMixin0:
    """Modal dialog showing unified audit log entries."""

    def __init__(self, app: object) -> None:
        super().__init__(app)
        self._AuditLogDialog__init__p1(app)
        self._AuditLogDialog__init__p2()

    def _load_log(self) -> None:
        # Toplevel dialogs sit outside the apply_form_theme walk — re-theme here.
        self.tree.apply_theme()
        filter_type = self._filter.get()
        log_type = None if filter_type == "all" else filter_type
        # Dedicated queries per filter so one type cannot crowd out the other.
        logs = self.app.db.list_audit_log(limit=500, log_type=log_type)

        rows: list[tuple] = []
        for entry in logs:
            entry_type = entry.get("log_type", "")
            if entry_type == "tax_change":
                rows.append(
                    (
                        "Tax Change",
                        entry.get("client_name", "") or "—",
                        entry.get("field", "") or "—",
                        entry.get("old_value", "") or "—",
                        entry.get("new_value", "") or "—",
                        entry.get("timestamp", "") or "—",
                    )
                )
            else:
                rows.append(
                    (
                        "Sync Conflict",
                        entry.get("table_name", "") or "—",
                        entry.get("global_id", "") or "—",
                        entry.get("direction", "") or "—",
                        "—",
                        entry.get("timestamp", "") or entry.get("logged_at", "") or "—",
                    )
                )
        # set_rows owns empty state + virtual rendering (500 rows → virtual).
        self.tree.set_rows(
            rows,
            iids=[str(i) for i in range(len(rows))],
            empty_message="No audit log entries found.",
        )
        if rows:
            self.feedback.set(f"{len(rows)} log entries loaded.", "info")

    def _clear_logs(self) -> None:
        from tkinter import messagebox

        if not messagebox.askyesno("Clear Logs", "Clear all sync conflict logs?", parent=self):
            return
        count = self.app.db.clear_sync_conflicts()
        self.feedback.success(f"Cleared {count} sync conflict log(s).")
        self._load_log()
