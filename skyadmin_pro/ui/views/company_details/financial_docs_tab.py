"""Company Details sub-tab."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from skyadmin_pro.config import (
    FINANCIAL_DOC_CATEGORIES,
    FINANCIAL_DOC_FOLDER_MAP,
    FINANCIAL_DOC_SUBCATEGORIES,
)
from skyadmin_pro.services.file_ops import (
    open_in_file_manager,
)
from skyadmin_pro.services.workflow import (
    resolve_client_folder,
)
from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import DatePickerField, make_modal, themed_entry


class FinancialDocsTabMixin:
    def _build_financial_docs(self, master) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(
            frame,
            text="Financial Documents",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        # Summary label
        self.fin_summary_label = ctk.CTkLabel(
            frame,
            text="",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=11),
        )
        self.fin_summary_label.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 4))

        # Filter row
        filter_row = ctk.CTkFrame(frame, fg_color="transparent")
        filter_row.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        filter_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(filter_row, text="Category:").grid(row=0, column=0, padx=(0, 8))
        self.fin_category_filter = ctk.CTkOptionMenu(
            filter_row,
            values=["All"] + list(FINANCIAL_DOC_CATEGORIES),
            command=lambda _: self._refresh_financial_docs(),
        )
        self.fin_category_filter.grid(row=0, column=1, sticky="w")
        self.fin_category_filter.set("All")

        # Treeview
        self.fin_doc_tree = ThemedTreeview(
            frame,
            columns=(
                ("date", "Date", 90),
                ("category", "Category", 110),
                ("subcategory", "From", 90),
                ("file", "File Name", 200),
                ("amount", "Amount", 100),
                ("desc", "Description", 180),
            ),
            table_id="company.fin_docs",
            db=self.app.db,
        )
        self.fin_doc_tree.tree.configure(height=8)
        self.fin_doc_tree.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 8))

        # Buttons
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 14))
        btn_row.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkButton(
            btn_row,
            text="Add Document",
            width=120,
            command=self._add_financial_doc,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            btn_row,
            text="Open File",
            width=100,
            fg_color="transparent",
            border_width=1,
            command=self._open_financial_doc,
        ).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ctk.CTkButton(
            btn_row,
            text="Delete",
            width=80,
            fg_color="transparent",
            border_width=1,
            text_color=("#b91c1c", "#f87171"),
            command=self._delete_financial_doc,
        ).grid(row=0, column=2, sticky="w", padx=(8, 0))

        return frame

    def _refresh_financial_docs(self) -> None:
        client_id = self._selected_client_id()
        self.fin_doc_tree.apply_theme()
        if client_id is None:
            self.fin_doc_tree.set_rows([], empty_message="Select a client to view financial documents.")
            self.fin_summary_label.configure(text="")
            return
        cat_filter = self.fin_category_filter.get()
        category = None if cat_filter == "All" else cat_filter
        docs = self.app.db.list_financial_documents(client_id, category)
        summary = self.app.db.financial_doc_summary(client_id)
        total = sum(summary.values())
        parts = [f"{cat}: {n}" for cat, n in sorted(summary.items())]
        self.fin_summary_label.configure(text=f"{total} document(s)" + (f" — {', '.join(parts)}" if parts else ""))
        rows, iids = [], []
        for d in docs:
            rows.append(
                (
                    d.get("doc_date") or "—",
                    d.get("category") or "—",
                    d.get("subcategory") or "—",
                    d.get("file_name") or "—",
                    d.get("amount") or "—",
                    d.get("description") or "—",
                )
            )
            iids.append(str(d["id"]))
        self.fin_doc_tree.set_rows(rows, iids=iids, empty_message="No financial documents for this client yet.")

    def _add_financial_doc(self) -> None:
        from skyadmin_pro.config import FINANCIAL_DOC_CATEGORIES

        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        file_path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Select financial document",
            filetypes=[
                ("All supported", "*.pdf *.jpg *.jpeg *.png *.xlsx *.xls *.csv"),
                ("PDF files", "*.pdf"),
                ("Images", "*.jpg *.jpeg *.png"),
                ("Excel", "*.xlsx *.xls *.csv"),
                ("All files", "*.*"),
            ],
        )
        if not file_path:
            return
        import os

        file_name = os.path.basename(file_path)
        # Build category selection dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Document Details")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        make_modal(dialog)
        ctk.CTkLabel(dialog, text="Category:").grid(row=0, column=0, padx=16, pady=(12, 4), sticky="w")
        cat_var = ctk.StringVar(value=FINANCIAL_DOC_CATEGORIES[0])
        ctk.CTkOptionMenu(dialog, values=list(FINANCIAL_DOC_CATEGORIES), variable=cat_var).grid(
            row=0, column=1, padx=(0, 16), pady=(12, 4), sticky="ew"
        )
        ctk.CTkLabel(dialog, text="From:").grid(row=1, column=0, padx=16, pady=(4, 4), sticky="w")
        sub_var = ctk.StringVar(value=FINANCIAL_DOC_SUBCATEGORIES[0])
        ctk.CTkOptionMenu(dialog, values=list(FINANCIAL_DOC_SUBCATEGORIES), variable=sub_var).grid(
            row=1, column=1, padx=(0, 16), pady=(4, 4), sticky="ew"
        )
        ctk.CTkLabel(dialog, text="Amount:").grid(row=2, column=0, padx=16, pady=(4, 4), sticky="w")
        amt_var = ctk.StringVar()
        themed_entry(dialog, textvariable=amt_var, width=200).grid(
            row=2, column=1, padx=(0, 16), pady=(4, 4), sticky="ew"
        )
        ctk.CTkLabel(dialog, text="Date:").grid(row=3, column=0, padx=16, pady=(4, 4), sticky="w")
        date_var = ctk.StringVar(value=date.today().isoformat())
        DatePickerField(dialog, var=date_var).grid(row=3, column=1, padx=(0, 16), pady=(4, 4), sticky="ew")
        ctk.CTkLabel(dialog, text="Description:").grid(row=4, column=0, padx=16, pady=(4, 4), sticky="w")
        desc_var = ctk.StringVar()
        themed_entry(dialog, textvariable=desc_var, width=200).grid(
            row=4, column=1, padx=(0, 16), pady=(4, 4), sticky="ew"
        )

        def _confirm() -> None:
            category = cat_var.get()
            subcategory = sub_var.get()
            # Copy file to workspace
            client = self.app.db.get_client(client_id)
            client_name = (client or {}).get("name") or "client"
            folder_name = FINANCIAL_DOC_FOLDER_MAP.get(category, "General_Expenses")
            try:
                client_folder = resolve_client_folder(self.app.paths.clients, client_name, create=True)
            except Exception as exc:
                self.feedback.error(str(exc))
                return
            dest_dir = client_folder / "04_Financial_Docs" / folder_name
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                self.feedback.error(f"Cannot create document folder: {exc}")
                return
            dest_path = dest_dir / file_name
            # Prevent duplicate file copies — add numeric suffix if exists
            if dest_path.exists():
                stem = dest_path.stem
                suffix = dest_path.suffix
                counter = 1
                while dest_path.exists():
                    dest_path = dest_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            try:
                import shutil

                shutil.copy2(file_path, dest_path)
                stored = str(dest_path)
            except Exception:
                stored = ""
            self.app.db.add_financial_document(
                client_id=client_id,
                category=category,
                subcategory=subcategory,
                file_name=dest_path.name,
                file_path=file_path,
                stored_path=stored,
                amount=amt_var.get().strip(),
                doc_date=date_var.get().strip(),
                description=desc_var.get().strip(),
            )
            dialog.destroy()
            self.feedback.success(f"Document '{dest_path.name}' added.")
            self._refresh_financial_docs()

        ctk.CTkButton(
            dialog,
            text="Add",
            width=100,
            command=_confirm,
        ).grid(row=5, column=0, columnspan=2, pady=(12, 16))

    def _open_financial_doc(self) -> None:
        selected = self.fin_doc_tree.tree.selection()
        if not selected:
            self.feedback.error("Select a document first.")
            return
        doc_id = int(selected[0])
        doc = self.app.db.get_financial_document(doc_id)
        if not doc:
            return
        path = doc.get("stored_path") or doc.get("file_path") or ""
        if not path or not os.path.exists(path):
            self.feedback.error("File not found on disk.")
            return
        try:
            open_in_file_manager(Path(path))
        except (OSError, RuntimeError) as exc:
            self.feedback.error(f"Could not open file: {exc}")

    def _delete_financial_doc(self) -> None:
        selected = self.fin_doc_tree.tree.selection()
        if not selected:
            self.feedback.error("Select a document first.")
            return
        import tkinter.messagebox as mb

        if not mb.askyesno(
            "Delete",
            "Delete this financial document?",
            parent=self.winfo_toplevel(),
        ):
            return
        doc_id = int(selected[0])
        doc = self.app.db.delete_financial_document(doc_id)
        if doc:
            stored = doc.get("stored_path") or ""
            if stored and os.path.exists(stored):
                try:
                    os.remove(stored)
                except OSError:
                    pass
        self.feedback.success("Document deleted.")
        self._refresh_financial_docs()
