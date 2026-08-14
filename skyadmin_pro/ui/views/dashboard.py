"""Dashboard: counts, 45-day expiry alerts, and a pending-task snapshot."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import EXPIRY_ALERT_DAYS, NAV_DATABASE_TASKS
from skyadmin_pro.services.file_ops import open_in_file_manager
from skyadmin_pro.services.tracking import classify_expiry, days_until, expiry_label
from skyadmin_pro.services.workflow import (
    copy_to_clipboard,
    create_client_workspace,
    format_eod_report,
)
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.widgets import FeedbackLabel


class DashboardView(BaseView):
    title = "Dashboard"
    subtitle = "Live overview of pending work and document expiry alerts."

    def build(self) -> None:
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(2, weight=1)

        self._cards = ctk.CTkFrame(self.body, fg_color="transparent")
        self._cards.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        for index in range(4):
            self._cards.grid_columnconfigure(index, weight=1)

        self.card_pending = self._stat_card(self._cards, 0, "Pending tasks", "0")
        self.card_done = self._stat_card(self._cards, 1, "Completed today", "0")
        self.card_expiring = self._stat_card(self._cards, 2, f"Expiring in {EXPIRY_ALERT_DAYS} days", "0")
        self.card_clients = self._stat_card(self._cards, 3, "Clients", "0")

        workflow = ctk.CTkFrame(self.body, corner_radius=12)
        workflow.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        workflow.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(
            workflow,
            text="Copy EOD report",
            width=160,
            command=self._copy_eod,
        ).grid(row=0, column=0, padx=(16, 8), pady=14, sticky="w")

        self.onboard_var = ctk.StringVar()
        ctk.CTkEntry(
            workflow,
            textvariable=self.onboard_var,
            placeholder_text="New client name",
            width=220,
        ).grid(row=0, column=1, padx=(8, 8), pady=14)
        ctk.CTkButton(
            workflow,
            text="Generate Workspace",
            width=170,
            command=self._generate_workspace,
        ).grid(row=0, column=2, padx=(0, 16), pady=14, sticky="w")

        self.workflow_feedback = FeedbackLabel(workflow)
        self.workflow_feedback.grid(row=1, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 12))

        split = ctk.CTkFrame(self.body, fg_color="transparent")
        split.grid(row=2, column=0, sticky="nsew")
        split.grid_columnconfigure(0, weight=3)
        split.grid_columnconfigure(1, weight=2)
        split.grid_rowconfigure(0, weight=1)

        expiry_card = ctk.CTkFrame(split, corner_radius=12)
        expiry_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        expiry_card.grid_columnconfigure(0, weight=1)
        expiry_card.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(expiry_card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Expiry alerts — passports & licenses",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            header,
            text="Open tasks",
            width=110,
            command=lambda: self.app.show_view(NAV_DATABASE_TASKS),
        ).grid(row=0, column=1, sticky="e")

        self.expiry_tree = ThemedTreeview(
            expiry_card,
            columns=(
                ("client", "Client", 160),
                ("type", "Document", 140),
                ("expiry", "Expiry date", 110),
                ("status", "Status", 160),
            ),
        )
        self.expiry_tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.expiry_hint = ctk.CTkLabel(
            expiry_card,
            text="Expired = red · ≤14 days = orange · ≤45 days = yellow",
            text_color=("gray40", "gray70"),
            anchor="w",
        )
        self.expiry_hint.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 12))

        pending_card = ctk.CTkFrame(split, corner_radius=12)
        pending_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        pending_card.grid_columnconfigure(0, weight=1)
        pending_card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            pending_card,
            text="Pending tasks",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))
        self.pending_tree = ThemedTreeview(
            pending_card,
            columns=(
                ("client", "Client", 120),
                ("title", "Task", 180),
                ("due", "Due", 90),
            ),
        )
        self.pending_tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _stat_card(self, master, column: int, label: str, value: str) -> ctk.CTkLabel:
        card = ctk.CTkFrame(master, corner_radius=12, height=92)
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 0))
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=label, text_color=("gray40", "gray70"), anchor="w").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 0)
        )
        value_label = ctk.CTkLabel(
            card, text=value, font=ctk.CTkFont(size=26, weight="bold"), anchor="w"
        )
        value_label.grid(row=1, column=0, sticky="w", padx=16, pady=(2, 12))
        return value_label

    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        counts = self.app.db.dashboard_counts(EXPIRY_ALERT_DAYS)
        self.card_pending.configure(text=str(counts["pending"]))
        self.card_done.configure(text=str(counts["completed_today"]))
        self.card_expiring.configure(text=str(counts["expiring"]))
        self.card_clients.configure(text=str(counts["clients"]))
        if counts["expiring"]:
            self.card_expiring.configure(text_color=("#b45309", "#fbbf24"))
        else:
            self.card_expiring.configure(text_color=("gray10", "gray90"))

        self.expiry_tree.apply_theme()
        self.pending_tree.apply_theme()

        expiring = self.app.db.list_expiring_documents(EXPIRY_ALERT_DAYS)
        rows = []
        tags = []
        iids = []
        for item in expiring:
            left = days_until(item.get("expiry_date"))
            if left is None:
                continue
            rows.append(
                (
                    item.get("client_name") or "—",
                    item.get("document_type") or "—",
                    item.get("expiry_date") or "—",
                    expiry_label(left),
                )
            )
            tags.append((classify_expiry(left),))
            iids.append(str(item["id"]))
        self.expiry_tree.set_rows(rows, iids=iids, tags=tags)

        pending = self.app.db.list_tasks(status="pending")[:12]
        self.pending_tree.set_rows(
            [
                (
                    item.get("client_name") or "—",
                    item.get("title") or "—",
                    item.get("due_date") or "—",
                )
                for item in pending
            ],
            iids=[str(item["id"]) for item in pending],
        )

    def _copy_eod(self) -> None:
        tasks = self.app.db.list_completed_today()
        report = format_eod_report(tasks)
        try:
            copy_to_clipboard(report, tk_window=self.app)
        except Exception as exc:
            self.workflow_feedback.error(str(exc))
            return
        if tasks:
            self.workflow_feedback.success(
                f"EOD report copied ({len(tasks)} completed task(s)). Paste into chat or email."
            )
        else:
            self.workflow_feedback.info("No completed tasks today — empty report copied.")
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
        self.workflow_feedback.success(
            f"Workspace ready: {folder.name}/01_Company_Setup, 02_Accounting, 03_Visa"
        )
        self.app.set_status(f"Created client workspace at {folder}")
        self.refresh()
        try:
            open_in_file_manager(folder)
        except Exception as exc:
            self.workflow_feedback.info(str(exc))
