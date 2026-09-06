"""Global search dialog — searches across clients, tasks, documents, and contacts."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import (
    CONTENT_PAD,
    TEXT_MUTED,
)
from skyadmin_pro.ui.widgets import FeedbackLabel, themed_entry


class GlobalSearchDialog(ctk.CTkToplevel):
    """Modal search dialog that queries across all data types."""

    def __init__(self, app: object) -> None:
        super().__init__(app)
        self.app = app
        self.title("Global Search")
        self.geometry("700x520")
        self.resizable(True, True)
        self.transient(app)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Search input ──────────────────────────────────────────────
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.grid(row=0, column=0, sticky="ew", padx=CONTENT_PAD, pady=(CONTENT_PAD, 8))
        input_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(input_frame, text="Search:", font=ctk.CTkFont(size=13)).grid(row=0, column=0, padx=(0, 8))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._schedule_search())
        search_entry = themed_entry(
            input_frame,
            textvariable=self.search_var,
            placeholder_text="Type to search clients, tasks, documents, contacts…",
        )
        search_entry.grid(row=0, column=1, sticky="ew")
        search_entry.focus_set()
        self.bind("<Escape>", lambda _: self.destroy())

        # ── Filter tabs ───────────────────────────────────────────────
        self._filter = ctk.StringVar(value="all")
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(row=1, column=0, sticky="ew", padx=CONTENT_PAD, pady=(0, 8))

        for label, value in [
            ("All", "all"),
            ("Clients", "clients"),
            ("Tasks", "tasks"),
            ("Docs", "docs"),
            ("Contacts", "contacts"),
        ]:
            ctk.CTkRadioButton(
                filter_frame,
                text=label,
                variable=self._filter,
                value=value,
                command=self._run_search,
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=(0, 12))

        # ── Results ───────────────────────────────────────────────────
        self._results_frame = ctk.CTkScrollableFrame(self, corner_radius=8)
        self._results_frame.grid(row=2, column=0, sticky="nsew", padx=CONTENT_PAD, pady=(0, 8))
        self._results_frame.grid_columnconfigure(0, weight=1)

        self.feedback = FeedbackLabel(self)
        self.feedback.grid(row=3, column=0, sticky="ew", padx=CONTENT_PAD, pady=(0, CONTENT_PAD))

        self._search_after = None
        self._last_query = ""
        self._search_seq = 0

    def destroy(self) -> None:
        try:
            if self._search_after is not None:
                self.after_cancel(self._search_after)
        except Exception:
            pass
        self._search_after = None
        super().destroy()

    def _schedule_search(self) -> None:
        if self._search_after is not None:
            try:
                self.after_cancel(self._search_after)
            except Exception:
                pass
            self._search_after = None
        try:
            self._search_after = self.after(250, self._run_search)
        except Exception:
            self._search_after = None

    def _run_search(self) -> None:
        from skyadmin_pro.ui.async_ui import run_background

        self._search_after = None
        query = self.search_var.get().strip()
        if query == self._last_query:
            return
        self._last_query = query

        # Clear previous results
        for widget in self._results_frame.winfo_children():
            widget.destroy()

        if not query:
            self.feedback.info("Type at least 2 characters to search.")
            return

        if len(query) < 2:
            self.feedback.info("Type at least 2 characters.")
            return

        filter_type = self._filter.get()
        self._search_seq = int(getattr(self, "_search_seq", 0)) + 1
        seq = self._search_seq
        self.feedback.info("Searching…")

        def work():
            return self._search_all(query, filter_type)

        def on_success(results) -> None:
            if seq != getattr(self, "_search_seq", 0):
                return
            try:
                exists = self.winfo_exists()
            except Exception:
                return
            if not exists:
                return
            self._render_results(results, query)

        def on_error(msg: str) -> None:
            if seq != getattr(self, "_search_seq", 0):
                return
            try:
                self.feedback.error(f"Search failed: {msg}")
            except Exception:
                pass

        run_background(self, work=work, on_success=on_success, on_error=on_error)

    def _search_all(self, query: str, filter_type: str) -> list[dict]:
        db = self.app.db
        results: list[dict] = []

        if filter_type in ("all", "clients"):
            for row in db.search_clients(query):
                results.append(
                    {
                        "type": "Client",
                        "title": row.get("name", ""),
                        "subtitle": row.get("company_name") or row.get("email") or "",
                        "id": row.get("id"),
                        "nav": "database_tasks",
                    }
                )

        if filter_type in ("all", "tasks"):
            for row in db.list_tasks():
                title = row.get("title", "")
                if query.lower() in title.lower():
                    results.append(
                        {
                            "type": "Task",
                            "title": title,
                            "subtitle": row.get("category", ""),
                            "id": row.get("id"),
                            "nav": "database_tasks",
                        }
                    )

        if filter_type in ("all", "docs"):
            for row in db.list_documents():
                name = row.get("file_name", "") or row.get("document_type", "")
                if query.lower() in name.lower() or query.lower() in (row.get("document_type") or "").lower():
                    results.append(
                        {
                            "type": "Document",
                            "title": name,
                            "subtitle": f"{row.get('document_type', '')} — {row.get('client_name', '')}",
                            "id": row.get("id"),
                            "nav": "database_tasks",
                        }
                    )

        if filter_type in ("all", "contacts"):
            for row in db.list_office_contacts():
                name = row.get("name", "")
                if query.lower() in name.lower() or query.lower() in (row.get("organization") or "").lower():
                    results.append(
                        {
                            "type": "Contact",
                            "title": name,
                            "subtitle": row.get("role_title") or row.get("organization") or "",
                            "id": row.get("id"),
                            "nav": "office_hub",
                        }
                    )

        return results

    def _render_results(self, results: list[dict], query: str) -> None:
        if not results:
            self.feedback.info("No results found.")
            return

        self.feedback.success(f"{len(results)} result(s) found.")

        for i, item in enumerate(results):
            row = ctk.CTkFrame(self._results_frame, fg_color="transparent", corner_radius=6)
            row.grid(row=i, column=0, sticky="ew", pady=2)
            row.grid_columnconfigure(1, weight=1)
            row.configure(cursor="hand2")

            # Type badge — (light, dark) pairs; CTk resolves fg_color tuples
            # per appearance mode. Light variants are darkened for white text.
            badge_colors = {
                "Client": ("#2563eb", "#3b82f6"),
                "Task": ("#b45309", "#f59e0b"),
                "Document": ("#047857", "#10b981"),
                "Contact": ("#6d28d9", "#8b5cf6"),
            }
            badge = ctk.CTkLabel(
                row,
                text=item["type"],
                width=70,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=badge_colors.get(item["type"], ("#6b7280", "#9ca3af")),
                text_color="white",
                corner_radius=4,
            )
            badge.grid(row=0, column=0, rowspan=2, padx=(0, 8))

            # Title
            ctk.CTkLabel(
                row,
                text=item["title"],
                anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
            ).grid(row=0, column=1, sticky="sw")

            # Subtitle
            if item["subtitle"]:
                ctk.CTkLabel(
                    row,
                    text=item["subtitle"],
                    anchor="w",
                    font=ctk.CTkFont(size=11),
                    text_color=TEXT_MUTED,
                ).grid(row=1, column=1, sticky="nw")

            # Click handler — bind the row and its children so clicks on
            # the badge/title/subtitle labels navigate too.
            nav = item["nav"]

            def _navigate(_event, n=nav, owner=self) -> None:
                owner._navigate_and_close(n)

            row.bind("<Button-1>", _navigate)
            for child in row.winfo_children():
                try:
                    child.bind("<Button-1>", _navigate)
                except Exception:
                    pass

    def _navigate_and_close(self, nav_key: str) -> None:
        self.app.show_view(nav_key)
        self.destroy()
