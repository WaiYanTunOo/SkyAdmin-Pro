"""Document Hub — financial documents panel."""

from __future__ import annotations

import os
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from skyadmin_pro.services.file_ops import open_in_file_manager
from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.widgets import themed_entry


class FinancialDocsPanel(ctk.CTkFrame):
    """Cross-client search and browse for financial documents."""

    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_toolbar()
        self._build_treeview()
        self.refresh()

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
        bar.grid_columnconfigure(1, weight=3)
        bar.grid_columnconfigure(3, weight=1)
        bar.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(bar, text="Search:", font=("Segoe UI", 12)).grid(row=0, column=0, padx=(0, 4))
        self.search_var = ctk.StringVar()
        self._search_after: str | None = None
        self.search_entry = themed_entry(
            bar, textvariable=self.search_var, placeholder_text="File name, description..."
        )
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.search_entry.bind("<Return>", lambda _: self._do_search())
        self.search_var.trace_add("write", lambda *_: self._debounced_search())

        ctk.CTkLabel(bar, text="Category:", font=("Segoe UI", 12)).grid(row=0, column=2, padx=(0, 4))
        from skyadmin_pro.config import FINANCIAL_DOC_CATEGORIES

        self.cat_var = ctk.StringVar(value="All")
        self.cat_menu = ctk.CTkOptionMenu(
            bar,
            variable=self.cat_var,
            values=["All"] + list(FINANCIAL_DOC_CATEGORIES),
            width=140,
        )
        self.cat_menu.grid(row=0, column=3, sticky="ew", padx=(0, 8))

        ctk.CTkLabel(bar, text="Client:", font=("Segoe UI", 12)).grid(row=0, column=4, padx=(0, 4))
        self.client_var = ctk.StringVar(value="All")
        self.client_menu = ctk.CTkOptionMenu(
            bar,
            variable=self.client_var,
            values=["All"],
            width=180,
        )
        self.client_menu.grid(row=0, column=5, sticky="ew", padx=(0, 8))

        ctk.CTkButton(bar, text="Search", width=70, command=self._do_search).grid(row=0, column=6, padx=(0, 4))
        ctk.CTkButton(
            bar, text="Clear", width=60, fg_color="transparent", border_width=1, command=self._clear_search
        ).grid(row=0, column=7, padx=(0, 4))
        ctk.CTkButton(bar, text="Open", width=60, command=self._open_selected).grid(row=0, column=8, padx=(0, 4))
        ctk.CTkButton(bar, text="Refresh", width=70, command=self.refresh).grid(row=0, column=9)

    def _build_treeview(self) -> None:
        from skyadmin_pro.ui.treeview import ThemedTreeview

        self.tree = ThemedTreeview(
            self,
            columns=(
                ("client", "Client", 160),
                ("date", "Date", 90),
                ("category", "Category", 120),
                ("filename", "File Name", 200),
                ("amount", "Amount", 90),
                ("description", "Description", 200),
            ),
            showheight=12,
            on_double_click=self._on_tree_double,
        )
        self.tree.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        summary_frame.grid(row=2, column=0, sticky="ew", padx=4, pady=(0, 4))
        self.summary_label = ctk.CTkLabel(summary_frame, text="", font=("Segoe UI", 11), text_color=TEXT_MUTED)
        self.summary_label.pack(side="left")

    def _populate_client_menu(self) -> None:
        clients = self.app.db.list_clients()
        names = sorted(c.get("name", "") for c in clients if c.get("name"))
        self.client_menu.configure(values=["All"] + names)
        # Preserve the current selection; only reset when it no longer exists.
        if self.client_var.get() not in ("All",) + tuple(names):
            self.client_var.set("All")

    def _debounced_search(self) -> None:
        if self._search_after is not None:
            try:
                self.after_cancel(self._search_after)
            except Exception:
                pass
        self._search_after = self.after(300, self._do_search)

    def _clear_search(self) -> None:
        if self._search_after is not None:
            try:
                self.after_cancel(self._search_after)
            except Exception:
                pass
            self._search_after = None
        self.search_var.set("")
        self.cat_var.set("All")
        self.client_var.set("All")
        self._do_search()

    def _on_tree_double(self, iid: str | None) -> None:
        if iid is not None:
            try:
                self.tree.tree.selection_set(iid)
            except Exception:
                pass
        self._open_selected()

    def refresh(self) -> None:
        self._populate_client_menu()
        self._do_search()

    def _do_search(self) -> None:
        keyword = self.search_var.get().strip()
        cat_filter = self.cat_var.get()
        client_filter = self.client_var.get()

        rows = self.app.db.search_financial_documents(keyword) if keyword else self.app.db.all_financial_documents()

        if cat_filter != "All":
            rows = [r for r in rows if r.get("category") == cat_filter]
        if client_filter != "All":
            rows = [r for r in rows if r.get("client_name") == client_filter]
        # Cap at 200 for Windows Treeview virtual threshold (avoids 1000+ insert jank)
        if len(rows) > 200:
            rows = rows[:200]

        tree_rows = []
        tree_iids = []
        for doc in rows:
            tree_rows.append(
                (
                    doc.get("client_name", ""),
                    doc.get("doc_date") or "",
                    doc.get("category") or "",
                    doc.get("file_name") or "",
                    doc.get("amount") or "",
                    doc.get("description") or "",
                )
            )
            tree_iids.append(str(doc["id"]))
        self.tree.set_rows(tree_rows, iids=tree_iids, empty_message="No financial documents found.")

        cats = {}
        for doc in rows:
            c = doc.get("category") or "Uncategorized"
            cats[c] = cats.get(c, 0) + 1
        parts = [f"{v} {k}" for k, v in sorted(cats.items())]
        self.summary_label.configure(
            text=f"{len(rows)} document(s) — {', '.join(parts)}" if parts else "No documents found"
        )

    def _open_selected(self) -> None:
        selected = self.tree.tree.selection()
        if not selected:
            return
        doc_id = int(selected[0])
        doc = self.app.db.get_financial_document(doc_id)
        if not doc:
            return
        path = doc.get("stored_path") or doc.get("file_path") or ""
        if not path or not os.path.exists(path):
            messagebox.showwarning("SkyAdmin Pro", f"File not found:\n{path}")
            return
        try:
            open_in_file_manager(Path(path))
        except (OSError, RuntimeError) as exc:
            messagebox.showerror("SkyAdmin Pro", f"Could not open file:\n{exc}")
