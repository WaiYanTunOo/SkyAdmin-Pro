"""Audit log viewer — unified view of tax changes and sync conflicts."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CONTENT_PAD, CARD_RADIUS, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import FeedbackLabel


class AuditLogDialog(ctk.CTkToplevel):
    """Modal dialog showing unified audit log entries."""

    def __init__(self, app: object) -> None:
        super().__init__(app)
        self.app = app
        self.title("Audit Log")
        self.geometry("900x500")
        self.resizable(True, True)
        self.transient(app)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=CONTENT_PAD, pady=(CONTENT_PAD, 8))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header, text="Audit Log",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        self.feedback = FeedbackLabel(self)
        self.feedback.grid(row=2, column=0, sticky="ew", padx=CONTENT_PAD, pady=(0, CONTENT_PAD))

        # Filter buttons
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e")
        self._filter = ctk.StringVar(value="all")
        for label, val in [("All", "all"), ("Tax Changes", "tax_change"), ("Sync Conflicts", "sync_conflict")]:
            ctk.CTkRadioButton(
                btn_frame, text=label, variable=self._filter, value=val,
                command=self._load_log, font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=(0, 10))

        # Tree
        self.tree = ThemedTreeview(
            self,
            columns=(
                ("type", "Type", 110),
                ("client", "Client / Table", 180),
                ("field", "Field", 150),
                ("old", "Old Value", 150),
                ("new", "New Value", 150),
                ("timestamp", "Timestamp", 160),
            ),
            showheight=15,
            table_id="audit_log",
            db=self.app.db,
        )
        self.tree.grid(row=1, column=0, sticky="nsew", padx=CONTENT_PAD, pady=(0, 8))

        # Footer
        ctk.CTkButton(
            self, text="Clear All Logs", width=120,
            fg_color=("#dc2626", "#b91c1c"), hover_color="#b91c1c",
            command=self._clear_logs,
        ).grid(row=3, column=0, sticky="w", padx=CONTENT_PAD, pady=(0, CONTENT_PAD))

        ctk.CTkButton(
            self, text="Close", width=80,
            command=self.destroy,
        ).grid(row=3, column=0, sticky="e", padx=CONTENT_PAD, pady=(0, CONTENT_PAD))

        self._load_log()

    def _load_log(self) -> None:
        # Toplevel dialogs sit outside the apply_form_theme walk — re-theme here.
        self.tree.apply_theme()
        logs = self.app.db.list_audit_log(limit=500)
        filter_type = self._filter.get()
        if filter_type != "all":
            logs = [l for l in logs if l.get("log_type") == filter_type]

        rows: list[tuple] = []
        for entry in logs:
            log_type = entry.get("log_type", "")
            if log_type == "tax_change":
                rows.append((
                    "Tax Change",
                    entry.get("client_name", "") or "—",
                    entry.get("field", "") or "—",
                    entry.get("old_value", "") or "—",
                    entry.get("new_value", "") or "—",
                    entry.get("timestamp", "") or "—",
                ))
            else:
                rows.append((
                    "Sync Conflict",
                    entry.get("table_name", "") or "—",
                    entry.get("global_id", "") or "—",
                    entry.get("direction", "") or "—",
                    "—",
                    entry.get("timestamp", "") or "—",
                ))
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
