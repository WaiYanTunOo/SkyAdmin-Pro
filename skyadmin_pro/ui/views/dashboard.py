"""Dashboard: counts, next actions, expiry alerts, overdue payments, pending
tasks, and client month closes."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox

import customtkinter as ctk

from skyadmin_pro.config import NAV_DATABASE_TASKS
from skyadmin_pro.services.file_ops import open_in_file_manager
from skyadmin_pro.services.snippets import effective_text, load_snippet_overrides
from skyadmin_pro.services.tracking import (
    classify_expiry,
    days_until,
    effective_expiry_date,
    expiry_label,
)
from skyadmin_pro.services.workflow import (
    copy_to_clipboard,
    create_client_workspace,
    format_eod_report,
)
from skyadmin_pro.ui.theme import (
    CANVAS_BG,
    CANVAS_TEXT,
    CANVAS_VALUE_TEXT,
    CARD_TITLE_SIZE,
    TEXT_MUTED,
)
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.widgets import FeedbackLabel, MonthStatusPanel


def _days_since(start: str | None, today: str) -> str:
    """Whole days between a YYYY-MM-DD start and today ('—' if unknown)."""
    if not start or len(start) < 10:
        return "—"
    try:
        delta = (date.fromisoformat(today) - date.fromisoformat(start[:10])).days
    except ValueError:
        return "—"
    return f"{delta} day(s)" if delta >= 0 else "—"


class DashboardView(BaseView):
    title = "Dashboard"
    subtitle = "Live overview of pending work and document expiry alerts."

    def build(self) -> None:
        self.body.grid_rowconfigure(0, weight=1)
        self._scroll = ctk.CTkScrollableFrame(self.body, fg_color="transparent")
        self._scroll.grid(row=0, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)
        self._scroll.grid_rowconfigure(5, weight=1)

        # -- Row 1: core operational cards --
        self._row1 = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._row1.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        for i in range(5):
            self._row1.grid_columnconfigure(i, weight=1)

        self.card_pending = self._stat_card(self._row1, 0, "Pending tasks", "0")
        self.card_done = self._stat_card(self._row1, 1, "Completed today", "0")
        self.card_expiring = self._stat_card(self._row1, 2, "Expiry alerts", "0")
        self.card_overdue = self._stat_card(self._row1, 3, "Overdue payments", "0")
        self.card_clients = self._stat_card(self._row1, 4, "Clients", "0")

        # -- Row 2: financial / accounting cards --
        self._row2 = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._row2.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        for i in range(5):
            self._row2.grid_columnconfigure(i, weight=1)

        self.card_supplier = self._stat_card(self._row2, 0, "Supplier due", "0")
        self.card_ongoing = self._stat_card(self._row2, 1, "Ongoing services", "0")
        self.card_pending_filings = self._stat_card(self._row2, 2, "Tax filings pending", "0")
        self.card_revenue = self._stat_card(self._row2, 3, "Monthly revenue", "0")
        self.card_vo_csh = self._stat_card(self._row2, 4, "VO/CSH expiring", "0")

        # -- Row 1.5: expiry timeline chart --
        timeline_card = ctk.CTkFrame(self._scroll, corner_radius=12)
        timeline_card.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        timeline_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            timeline_card,
            text="Expiry Timeline — next 45 days",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))
        self.timeline_canvas = tk.Canvas(
            timeline_card,
            height=120,
            bg=ctk.ThemeManager.theme["CTkFrame"]["fg_color"][1 if ctk.get_appearance_mode() == "Dark" else 0],
            highlightthickness=0,
        )
        self.timeline_canvas.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))

        workflow = ctk.CTkFrame(self._scroll, corner_radius=12)
        workflow.grid(row=3, column=0, sticky="ew", pady=(0, 12))
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

        folders = ctk.CTkFrame(workflow, fg_color="transparent")
        folders.grid(row=1, column=0, columnspan=3, sticky="ew", padx=16)
        folders.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(
            folders,
            text="Open Workspace",
            width=130,
            fg_color="transparent",
            border_width=1,
            command=lambda: self._open_folder(self.app.paths.root),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            folders,
            text="Open Clients",
            width=130,
            fg_color="transparent",
            border_width=1,
            command=lambda: self._open_folder(self.app.paths.clients),
        ).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ctk.CTkButton(
            folders,
            text="Open Suppliers",
            width=130,
            fg_color="transparent",
            border_width=1,
            command=lambda: self._open_folder(self.app.paths.suppliers),
        ).grid(row=0, column=2, sticky="w", padx=(8, 0))

        self.workflow_feedback = FeedbackLabel(workflow)
        self.workflow_feedback.grid(row=2, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 12))

        next_card = ctk.CTkFrame(self._scroll, corner_radius=12)
        next_card.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        next_card.grid_columnconfigure(0, weight=1)
        next_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            next_card,
            text="Next actions",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(
            next_card,
            text="Real pending work, worst first: unpaid invoices, expiring services, and due tasks.",
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        self.next_tree = ThemedTreeview(
            next_card,
            columns=(
                ("action", "Action", 320),
                ("client", "Client", 190),
                ("when", "When", 200),
            ),
            on_select=self._next_selected,
        )
        self.next_tree.tree.configure(height=10)
        self.next_tree.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))

        self.month_panel = MonthStatusPanel(
            self._scroll, self.app, showheight=6, title="Client month closes — tax status"
        )
        self.month_panel.grid(row=5, column=0, sticky="ew", pady=(0, 12))

        split = ctk.CTkFrame(self._scroll, fg_color="transparent")
        split.grid(row=6, column=0, sticky="nsew")
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
            text="Expiry alerts — documents & supplier services",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
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
            text="Expired = red · ≤14 days = orange · within its alert window = yellow",
            text_color=TEXT_MUTED,
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
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
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

        ongoing = ctk.CTkFrame(self._scroll, corner_radius=12)
        ongoing.grid(row=7, column=0, sticky="ew", pady=(0, 12))
        ongoing.grid_columnconfigure(0, weight=1)
        ongoing_header = ctk.CTkFrame(ongoing, fg_color="transparent")
        ongoing_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        ongoing_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            ongoing_header,
            text="Ongoing services — active work in progress",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            ongoing_header,
            text="Open services",
            width=110,
            command=lambda: self.app.show_view(NAV_DATABASE_TASKS),
        ).grid(row=0, column=1, sticky="e")
        self.ongoing_tree = ThemedTreeview(
            ongoing,
            columns=(
                ("client", "Client", 200),
                ("type", "Service", 260),
                ("started", "Started", 110),
                ("since", "In progress", 110),
            ),
            on_select=self._ongoing_selected,
        )
        self.ongoing_tree.tree.configure(height=4)
        self.ongoing_tree.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))

        overdue = ctk.CTkFrame(self._scroll, corner_radius=12)
        overdue.grid(row=8, column=0, sticky="ew", pady=(0, 12))
        overdue.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            overdue,
            text="Overdue payments — past due date, not yet marked paid",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))
        self.overdue_tree = ThemedTreeview(
            overdue,
            columns=(
                ("client", "Client", 200),
                ("type", "Service", 240),
                ("amount", "Amount", 110),
                ("due", "Due date", 110),
            ),
        )
        self.overdue_tree.tree.configure(height=4)
        self.overdue_tree.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))
        overdue_controls = ctk.CTkFrame(overdue, fg_color="transparent")
        overdue_controls.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))
        ctk.CTkButton(
            overdue_controls,
            text="Copy invoice reminder",
            width=180,
            command=self._copy_overdue_reminder,
        ).pack(side="left")
        ctk.CTkButton(
            overdue_controls,
            text="Mark paid",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=self._mark_overdue_paid,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkLabel(
            overdue_controls,
            text="Select a row, then copy the reminder or clear it.",
            text_color=TEXT_MUTED,
        ).pack(side="right")

        supplier_due = ctk.CTkFrame(self._scroll, corner_radius=12)
        supplier_due.grid(row=9, column=0, sticky="ew", pady=(0, 12))
        supplier_due.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            supplier_due,
            text="Pending supplier payments — past due date, not yet paid",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))
        self.supplier_due_tree = ThemedTreeview(
            supplier_due,
            columns=(
                ("supplier", "Supplier", 200),
                ("client", "Client", 200),
                ("amount", "Amount", 110),
                ("due", "Due date", 110),
            ),
        )
        self.supplier_due_tree.tree.configure(height=4)
        self.supplier_due_tree.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))
        supplier_controls = ctk.CTkFrame(supplier_due, fg_color="transparent")
        supplier_controls.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))
        ctk.CTkButton(
            supplier_controls,
            text="Mark paid",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=self._mark_supplier_due_paid,
        ).pack(side="left")
        ctk.CTkLabel(
            supplier_controls,
            text="Select a row, then mark it paid.",
            text_color=TEXT_MUTED,
        ).pack(side="right")

        report_card = ctk.CTkFrame(self._scroll, corner_radius=12)
        report_card.grid(row=10, column=0, sticky="ew", pady=(0, 12))
        report_card.grid_columnconfigure(0, weight=1)
        report_card.grid_rowconfigure(1, weight=1)
        report_header = ctk.CTkFrame(report_card, fg_color="transparent")
        report_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        report_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            report_header,
            text="Monthly incentive report — new services signed up",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        now = date.today()
        self._report_months = []
        for i in range(12):
            m = now.month - i
            y = now.year
            while m <= 0:
                m += 12
                y -= 1
            self._report_months.append((y, m))
        month_labels = [f"{date(y, m, 1):%b %Y}" for y, m in self._report_months]
        self._report_month_var = ctk.StringVar(value=month_labels[0])
        ctk.CTkOptionMenu(
            report_header,
            variable=self._report_month_var,
            values=month_labels,
            width=140,
            command=lambda _: self._refresh_report(),
        ).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(
            report_header,
            text="Export Excel",
            width=110,
            command=self._export_report,
        ).grid(row=0, column=2, padx=(8, 0))

        self.report_tree = ThemedTreeview(
            report_card,
            columns=(
                ("client", "Client", 200),
                ("type", "Service", 240),
                ("amount", "Amount", 110),
                ("service_date", "Start date", 120),
                ("source", "Source", 90),
            ),
        )
        self.report_tree.tree.configure(height=6)
        self.report_tree.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))
        self.report_hint = ctk.CTkLabel(
            report_card,
            text="Completed services in the selected month. Click 'Export Excel' to download.",
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.report_hint.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 12))

        tax_overview = ctk.CTkFrame(self._scroll, corner_radius=12)
        tax_overview.grid(row=11, column=0, sticky="ew", pady=(0, 12))
        tax_overview.grid_columnconfigure(0, weight=1)
        tax_overview.grid_rowconfigure(1, weight=1)
        tax_header = ctk.CTkFrame(tax_overview, fg_color="transparent")
        tax_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        tax_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            tax_header,
            text="Tax cycle overview — accounting clients filing statuses",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            tax_header,
            text="Accounting setup",
            width=130,
            fg_color="transparent",
            border_width=1,
            command=self._open_accounting_setup,
        ).grid(row=0, column=3, sticky="e", padx=(8, 0))
        ctk.CTkButton(
            tax_header,
            text="VO/CSH setup",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=self._open_vo_csh_setup,
        ).grid(row=0, column=4, sticky="e", padx=(8, 0))
        ctk.CTkButton(
            tax_header,
            text="Open details",
            width=110,
            command=lambda: self.app.show_view(NAV_DATABASE_TASKS),
        ).grid(row=0, column=2, sticky="e")
        ctk.CTkButton(
            tax_header,
            text="Run Monthly Cycle",
            width=140,
            fg_color=("#15803d", "#16a34a"),
            command=self._run_monthly_cycle,
        ).grid(row=0, column=1, sticky="e", padx=(0, 8))
        self.tax_overview_tree = ThemedTreeview(
            tax_overview,
            columns=(
                ("client", "Client", 200),
                ("fs", "FS", 90),
                ("pnd53", "PND53", 90),
                ("pp30", "PP30", 90),
                ("pnd51", "PND51", 90),
                ("pnd50", "PND50", 90),
                ("audit", "Audit", 90),
                ("fee", "Fee", 100),
                ("paid", "Paid", 70),
            ),
        )
        self.tax_overview_tree.tree.configure(height=12)
        self.tax_overview_tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _stat_card(self, master, column: int, label: str, value: str) -> ctk.CTkLabel:
        card = ctk.CTkFrame(master, corner_radius=14, height=110)
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 0))
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text=label,
            text_color=TEXT_MUTED,
            anchor="w",
            wraplength=0,
            font=ctk.CTkFont(size=12),
        ).grid(row=0, column=0, sticky="nw", padx=16, pady=(18, 0))
        value_label = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=28, weight="bold"), anchor="w")
        value_label.grid(row=1, column=0, sticky="sw", padx=16, pady=(6, 16))
        return value_label

    def _draw_timeline(self) -> None:
        """Draw a bar-per-day expiry timeline for the next 45 days."""
        canvas = self.timeline_canvas
        canvas.delete("all")
        mode = ctk.get_appearance_mode()
        is_dark = mode == "Dark"
        bg = CANVAS_BG[1 if is_dark else 0]
        text_color = CANVAS_TEXT[1 if is_dark else 0]
        value_color = CANVAS_VALUE_TEXT[1 if is_dark else 0]
        canvas.configure(bg=bg)
        width = canvas.winfo_width()
        if width < 10:
            canvas.update_idletasks()
            width = max(canvas.winfo_width(), 600)
        height = int(canvas.cget("height"))

        expiring = self.app.db.list_expiring_documents()
        supplier_expiring = self.app.db.list_expiring_supplier_services()
        # Bucket by days-left
        buckets = {}
        for item in expiring:
            eff = effective_expiry_date(item.get("expiry_date"), item.get("document_type"))
            left = days_until(eff)
            if left is not None and 0 <= left <= 45:
                buckets[left] = buckets.get(left, 0) + 1
        for item in supplier_expiring:
            left = days_until(item.get("expiry_date"))
            if left is not None and 0 <= left <= 45:
                buckets[left] = buckets.get(left, 0) + 1

        max_count = max(buckets.values()) if buckets else 1
        bar_w = max(4, (width - 40) // 45)
        x0 = 20
        baseline = height - 24

        # Day labels
        for day in range(0, 46, 15):
            x = x0 + day * bar_w
            canvas.create_text(x, height - 8, text=f"d{day}", fill=text_color, font=("Segoe UI", 8))

        # Bars
        colors = {0: "#dc2626", 1: "#ea580c", 2: "#d97706"}
        for day in sorted(buckets):
            count = buckets[day]
            bh = max(3, int((count / max_count) * (height - 40)))
            color = colors.get(min(day // 7, 2), "#16a34a") if day <= 14 else "#16a34a"
            if day <= 7:
                color = "#dc2626"
            elif day <= 14:
                color = "#ea580c"
            elif day <= 30:
                color = "#d97706"
            x = x0 + day * bar_w
            canvas.create_rectangle(
                x - bar_w // 2,
                baseline - bh,
                x + bar_w // 2,
                baseline,
                fill=color,
                outline="",
                tags=f"bar_{day}",
            )
            if count > 1:
                canvas.create_text(
                    x,
                    baseline - bh - 10,
                    text=str(count),
                    fill=value_color,
                    font=("Segoe UI", 8),
                )
        # Legend
        lx = width - 180
        for txt, col in [("≤7d", "#dc2626"), ("≤14d", "#ea580c"), ("≤30d", "#d97706"), ("31-45d", "#16a34a")]:
            canvas.create_rectangle(lx, 6, lx + 8, 14, fill=col, outline="")
            canvas.create_text(lx + 12, 10, text=txt, anchor="w", fill=text_color, font=("Segoe UI", 8))
            lx += 45

    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        counts = self.app.db.dashboard_counts()

        self.card_pending.configure(text=str(counts["pending"]))
        self.card_done.configure(text=str(counts["completed_today"]))
        self.card_expiring.configure(text=str(counts["expiring"]))
        self.card_overdue.configure(text=str(counts["overdue"]))
        self.card_clients.configure(text=str(counts["clients"]))
        self.card_supplier.configure(text=str(counts["supplier_due"]))
        self.card_ongoing.configure(text=str(counts["ongoing"]))

        pending_filings = self.app.db.count_pending_filings()
        self.card_pending_filings.configure(text=str(pending_filings))
        revenue = self.app.db.get_revenue_summary(date.today().year, date.today().month)
        self.card_revenue.configure(text=f"{revenue:,}")
        vo_csh_expiring = self.app.db.count_vo_csh_expiring(30)
        self.card_vo_csh.configure(text=str(vo_csh_expiring))

        self.month_panel.refresh()
        self._refresh_report()
        self._refresh_tax_overview()
        self.timeline_canvas.after(50, self._draw_timeline)

        if counts["expiring"]:
            self.card_expiring.configure(text_color=("#b45309", "#fbbf24"))
        else:
            self.card_expiring.configure(text_color=("gray10", "gray90"))
        if counts["overdue"]:
            self.card_overdue.configure(text_color=("#b91c1c", "#f87171"))
        else:
            self.card_overdue.configure(text_color=("gray10", "gray90"))
        if counts["supplier_due"]:
            self.card_supplier.configure(text_color=("#b45309", "#fbbf24"))
        else:
            self.card_supplier.configure(text_color=("gray10", "gray90"))
        if counts["ongoing"]:
            self.card_ongoing.configure(text_color=("#15803d", "#4ade80"))
        else:
            self.card_ongoing.configure(text_color=("gray10", "gray90"))
        if pending_filings:
            self.card_pending_filings.configure(text_color=("#b45309", "#fbbf24"))
        else:
            self.card_pending_filings.configure(text_color=("gray10", "gray90"))
        if vo_csh_expiring:
            self.card_vo_csh.configure(text_color=("#b45309", "#fbbf24"))
        else:
            self.card_vo_csh.configure(text_color=("gray10", "gray90"))

        self.expiry_tree.apply_theme()
        self.pending_tree.apply_theme()
        self.overdue_tree.apply_theme()
        self.supplier_due_tree.apply_theme()
        self.ongoing_tree.apply_theme()
        self.next_tree.apply_theme()

        expiring = self.app.db.list_expiring_documents()
        supplier_expiring = self.app.db.list_expiring_supplier_services()
        overdue = self.app.db.list_overdue_services()
        supplier_due = self.app.db.list_pending_supplier_payments()
        pending = self.app.db.list_tasks(status="pending")
        ongoing = self.app.db.list_ongoing_services()
        renewal_due = self.app.db.list_renewal_items_due()
        self._refresh_next_actions(overdue, supplier_due, expiring, supplier_expiring, pending, ongoing, renewal_due)

        rows = []
        tags = []
        iids = []
        for item in expiring:
            eff = effective_expiry_date(item.get("expiry_date"), item.get("document_type"))
            left = days_until(eff)
            if left is None:
                continue
            tag = classify_expiry(left)
            rows.append(
                (
                    item.get("client_name") or "—",
                    item.get("document_type") or "—",
                    eff or "—",
                    expiry_label(left),
                )
            )
            tags.append((tag,) if tag else ())
            iids.append(str(item["id"]))
        for item in supplier_expiring:
            left = days_until(item.get("expiry_date"))
            if left is None:
                continue
            tag = classify_expiry(left)
            company = item.get("company_name") or "—"
            service = item.get("service_type") or "—"
            rows.append(
                (
                    item.get("supplier_name") or "—",
                    f"{company} · {service}",
                    item.get("expiry_date") or "—",
                    expiry_label(left),
                )
            )
            tags.append((tag,) if tag else ())
            iids.append(f"ss-{item['id']}")
        self.expiry_tree.set_rows(rows, iids=iids, tags=tags)

        self.overdue_tree.set_rows(
            [
                (
                    item.get("client_name") or "—",
                    item.get("document_type") or "—",
                    item.get("amount") or "—",
                    item.get("payment_date") or "—",
                )
                for item in overdue
            ],
            iids=[str(item["id"]) for item in overdue],
            tags=[("urgent",)] * len(overdue),
        )

        self.supplier_due_tree.set_rows(
            [
                (
                    item.get("supplier_name") or "—",
                    item.get("client_name") or "—",
                    item.get("amount") or "—",
                    item.get("due_date") or "—",
                )
                for item in supplier_due
            ],
            iids=[str(item["id"]) for item in supplier_due],
            tags=[("urgent",)] * len(supplier_due),
        )

        self.pending_tree.set_rows(
            [
                (
                    item.get("client_name") or "—",
                    item.get("title") or "—",
                    item.get("due_date") or "—",
                )
                for item in pending[:12]
            ],
            iids=[str(item["id"]) for item in pending[:12]],
        )

        today_iso = date.today().isoformat()
        self.ongoing_tree.set_rows(
            [
                (
                    item.get("client_name") or "—",
                    item.get("document_type") or "—",
                    item.get("start_date") or "—",
                    _days_since(item.get("start_date") or item.get("created_at"), today_iso),
                )
                for item in ongoing
            ],
            iids=[str(item["id"]) for item in ongoing],
            tags=[("wip",)] * len(ongoing),
        )

    def _refresh_next_actions(
        self,
        overdue=None,
        supplier_due=None,
        expiring=None,
        supplier_expiring=None,
        pending_tasks=None,
        ongoing=None,
        renewal_due=None,
    ) -> None:
        today = date.today().isoformat()
        overdue = self.app.db.list_overdue_services() if overdue is None else overdue
        supplier_due = self.app.db.list_pending_supplier_payments() if supplier_due is None else supplier_due
        expiring = self.app.db.list_expiring_documents() if expiring is None else expiring
        supplier_expiring = (
            self.app.db.list_expiring_supplier_services() if supplier_expiring is None else supplier_expiring
        )
        pending_tasks = self.app.db.list_tasks(status="pending") if pending_tasks is None else pending_tasks
        ongoing = self.app.db.list_ongoing_services() if ongoing is None else ongoing
        renewal_due = self.app.db.list_renewal_items_due() if renewal_due is None else renewal_due
        self._next_targets: dict[str, tuple[str, str]] = {}
        actions: list[tuple[int, str, tuple, str]] = []
        for item in overdue:
            actions.append(
                (
                    0,
                    "urgent",
                    (
                        "Collect overdue payment",
                        item.get("client_name") or "—",
                        f"{item.get('amount') or '—'} · due {item.get('payment_date') or '—'}",
                    ),
                    f"pay-{item['id']}",
                )
            )
        for item in supplier_due:
            actions.append(
                (
                    0,
                    "urgent",
                    (
                        "Pay supplier",
                        item.get("supplier_name") or "—",
                        f"{item.get('amount') or '—'} · due {item.get('due_date') or '—'}",
                    ),
                    f"sup-{item['id']}",
                )
            )
        for item in expiring:
            eff = effective_expiry_date(item.get("expiry_date"), item.get("document_type"))
            left = days_until(eff)
            if left is None:
                continue
            if left < 0:
                tag, priority = "expired", 1
            elif left <= 14:
                tag, priority = "urgent", 2
            else:
                tag, priority = "watch", 4
            client = item.get("client_name") or ""
            iid = f"exp-{item['id']}"
            actions.append(
                (
                    priority,
                    tag,
                    (
                        f"Renew {item.get('document_type')}",
                        client or "—",
                        expiry_label(left),
                    ),
                    iid,
                )
            )
            if client:
                self._next_targets[iid] = ("renewal", client)
        for item in supplier_expiring:
            left = days_until(item.get("expiry_date"))
            if left is None:
                continue
            if left < 0:
                tag, priority = "expired", 1
            elif left <= 14:
                tag, priority = "urgent", 2
            else:
                tag, priority = "watch", 4
            supplier = item.get("supplier_name") or "—"
            service = item.get("service_type") or "service"
            company = item.get("company_name") or ""
            when = f"{company} · {expiry_label(left)}" if company else expiry_label(left)
            iid = f"ss-{item['id']}"
            actions.append(
                (
                    priority,
                    tag,
                    (
                        f"Renew supplier service: {service}",
                        supplier,
                        when,
                    ),
                    iid,
                )
            )
        for item in ongoing:
            client = item.get("client_name") or ""
            iid = f"ongoing-{item['id']}"
            actions.append(
                (
                    3,
                    "watch",
                    (
                        f"Continue: {item.get('document_type')}",
                        client or "—",
                        "ongoing work — mark Completed when done",
                    ),
                    iid,
                )
            )
            if client:
                self._next_targets[iid] = ("company", client)
        for item in renewal_due:
            client = item.get("client_name") or ""
            when = expiry_label(item["days_left"])
            iid = f"ren-{item['client_id']}-{item['template_name'].replace(' ', '_')}"
            actions.append(
                (
                    2 if item["days_left"] <= 14 else 4,
                    "urgent" if item["days_left"] <= 14 else "watch",
                    (
                        f"Renewal prep: {item['template_name']}",
                        client or "—",
                        f"{item['due_count']} item(s) due · {when}",
                    ),
                    iid,
                )
            )
            if client:
                self._next_targets[iid] = ("renewal", client)
        for item in pending_tasks:
            if item.get("source_document_id"):
                continue  # ongoing-service task already listed above
            due = item.get("due_date") or ""
            overdue_task = bool(due) and due < today
            if item.get("pipeline_item_id"):
                iid = f"pipe-{item['id']}"
                self._next_targets[iid] = ("pipeline", "")
            else:
                iid = f"task-{item['id']}"
                self._next_targets[iid] = ("task", "")
            actions.append(
                (
                    1 if overdue_task else 3,
                    "urgent" if overdue_task else "watch",
                    (
                        f"Task: {item.get('title')}",
                        item.get("client_name") or "—",
                        f"due {due}" if due else "no due date",
                    ),
                    iid,
                )
            )
        actions.sort(key=lambda entry: entry[0])
        actions = actions[:12]
        self.next_tree.set_rows(
            [entry[2] for entry in actions],
            iids=[entry[3] for entry in actions],
            tags=[[entry[1]] for entry in actions],
        )

    def _next_selected(self, iid: str | None) -> None:
        if iid is None:
            return
        target = self._next_targets.get(iid)
        if not target:
            return
        kind, value = target
        tasks_view = self.app._views.get(NAV_DATABASE_TASKS)
        if tasks_view is None:
            return
        self.app.show_view(NAV_DATABASE_TASKS)
        if kind == "task" and iid.startswith("task-"):
            tasks_view.open_task(int(iid.split("-", 1)[1]))
        elif kind == "company":
            tasks_view.open_company_details(value)
        elif kind == "renewal":
            tasks_view.open_renewal(value)
        elif kind == "pipeline":
            tasks_view.open_pipeline()

    def _ongoing_selected(self, iid: str | None) -> None:
        if iid is None:
            return
        values = self.ongoing_tree.tree.item(iid, "values")
        if not values or values[0] in ("", "—"):
            return
        tasks_view = self.app._views.get(NAV_DATABASE_TASKS)
        if tasks_view is None:
            return
        self.app.show_view(NAV_DATABASE_TASKS)
        tasks_view.open_company_details(values[0])

    def _overdue_selected(self) -> int | None:
        iid = self.overdue_tree.selected_iid()
        return int(iid) if iid is not None else None

    def _copy_overdue_reminder(self) -> None:
        document_id = self._overdue_selected()
        if document_id is None:
            self.workflow_feedback.error("Select an overdue payment row first.")
            return
        item = self.app.db.get_document(document_id)
        if not item:
            return
        overrides = load_snippet_overrides(self.app.db.get_setting)
        template = effective_text("client", "Invoice payment reminder", overrides)
        if not template:
            self.workflow_feedback.error("Reminder template not found — add 'Invoice payment reminder' in Utilities.")
            return
        client = item.get("client_name") or ""
        message = (
            template.replace("[Client Contact Name]", client)
            .replace("[Client Company Name]", client)
            .replace("[Amount]", item.get("amount") or "")
            .replace("[Due Date]", item.get("payment_date") or "")
        )
        try:
            copy_to_clipboard(message, tk_window=self.app)
        except Exception as exc:
            self.workflow_feedback.error(str(exc))
            return
        self.workflow_feedback.success("Invoice reminder copied — paste into the email.")

    def _mark_overdue_paid(self) -> None:
        document_id = self._overdue_selected()
        if document_id is None:
            self.workflow_feedback.error("Select an overdue payment row first.")
            return
        self.app.db.set_document_paid(document_id, True)
        self.workflow_feedback.success("Marked as paid.")
        self.refresh()

    def _mark_supplier_due_paid(self) -> None:
        iid = self.supplier_due_tree.selected_iid()
        if iid is None:
            self.workflow_feedback.error("Select a pending supplier payment row first.")
            return
        self.app.db.set_supplier_payment_paid(int(iid), True)
        self.workflow_feedback.success("Supplier payment marked as paid.")
        self.refresh()

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
        self.refresh()
        try:
            open_in_file_manager(folder)
        except Exception as exc:
            self.workflow_feedback.info(str(exc))

    def _selected_report_month(self) -> tuple[int, int]:
        label = self._report_month_var.get()
        idx = [f"{date(y, m, 1):%b %Y}" for y, m in self._report_months].index(label)
        return self._report_months[idx]

    def _refresh_report(self) -> None:
        year, month = self._selected_report_month()
        rows = self.app.db.list_incentive_services(year, month)
        self.report_tree.set_rows(
            [
                (
                    row.get("client_name") or "—",
                    row.get("service") or "—",
                    row.get("amount") or "—",
                    (row.get("service_date") or "")[:10],
                    "Pipeline" if row.get("source") == "pipe" else "Document",
                )
                for row in rows
            ],
            iids=[row["id_key"] for row in rows],
        )

    def _export_report(self) -> None:
        year, month = self._selected_report_month()
        rows = self.app.db.list_incentive_services(year, month)
        if not rows:
            self.workflow_feedback.info("No completed services for this month.")
            return
        from skyadmin_pro.services.export import export_monthly_report

        label = self._report_month_var.get().replace(" ", "_")
        default_name = f"monthly_report_{label}.xlsx"
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx")],
            initialfile=default_name,
            title="Export monthly service report",
        )
        if not path:
            return
        try:
            from pathlib import Path

            export_monthly_report(self.app.db, year, month, Path(path))
        except Exception as exc:
            self.workflow_feedback.error(str(exc))
            return
        self.workflow_feedback.success(f"Report exported: {path}")

    def _open_accounting_setup(self) -> None:
        open_setup = getattr(self.app, "open_accounting_setup", None)
        if callable(open_setup):
            open_setup()
        else:
            self.app.show_view(NAV_DATABASE_TASKS)

    def _open_vo_csh_setup(self) -> None:
        open_setup = getattr(self.app, "open_vo_csh_setup", None)
        if callable(open_setup):
            open_setup()
        else:
            self.app.show_view(NAV_DATABASE_TASKS)

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
        self.refresh()

    def _refresh_tax_overview(self) -> None:
        self.tax_overview_tree.apply_theme()
        clients = self.app.db.list_accounting_clients()
        if not clients:
            self.tax_overview_tree.set_rows(
                [("No accounting clients configured yet.", "", "", "", "", "", "", "", "")],
                iids=["empty"],
                tags=[("inactive",)],
            )
            return
        status_icon = {
            "Complete": "\u2705",
            "On-Going": "\U0001f7e1",
            "Pending": "\u274c",
            "Not Applicable": "\u2b1c",
        }
        rows, iids, tags = [], [], []
        for c in clients:
            tag_list = []
            for field in ("fs_status", "pnd53_status", "pp30_status", "pnd51_status", "pnd50_status", "audit_status"):
                if c.get(field) == "Pending":
                    tag_list.append("urgent")
                    break
            fee = c.get("service_fee") or "\u2014"
            paid = c.get("payment_status") or "\u2014"
            rows.append(
                (
                    c.get("name") or "\u2014",
                    status_icon.get(c.get("fs_status") or "Not Applicable", "\u2b1c"),
                    status_icon.get(c.get("pnd53_status") or "Not Applicable", "\u2b1c"),
                    status_icon.get(c.get("pp30_status") or "Not Applicable", "\u2b1c"),
                    status_icon.get(c.get("pnd51_status") or "Not Applicable", "\u2b1c"),
                    status_icon.get(c.get("pnd50_status") or "Not Applicable", "\u2b1c"),
                    status_icon.get(c.get("audit_status") or "Not Applicable", "\u2b1c"),
                    fee,
                    paid,
                )
            )
            iids.append(str(c["id"]))
            tags.append(tuple(tag_list))
        self.tax_overview_tree.set_rows(rows, iids=iids, tags=tags)
