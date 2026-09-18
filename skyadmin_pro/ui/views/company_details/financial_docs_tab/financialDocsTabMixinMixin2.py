from __future__ import annotations

import os

import customtkinter as ctk

from skyadmin_pro.config import FINANCIAL_DOC_CATEGORIES
from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview


class FinancialDocsTabMixinMixin2:
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

    def _FinancialDocsTabMixin_build_financial_d_p1(self, master):
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(
            frame,
            text="Records for this company",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        # Summary label
        self.fin_summary_label = ctk.CTkLabel(
            frame,
            text="Not Document Hub folder tools.",
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

        from skyadmin_pro.ui.dnd import enable_drop

        enable_drop(frame, self._on_financial_doc_drop, enabled=True)
        return frame
