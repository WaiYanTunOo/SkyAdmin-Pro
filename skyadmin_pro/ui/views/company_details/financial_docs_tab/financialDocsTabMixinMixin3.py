from __future__ import annotations

import os
from datetime import date
from tkinter import filedialog

import customtkinter as ctk

from skyadmin_pro.config import FINANCIAL_DOC_SUBCATEGORIES
from skyadmin_pro.ui.widgets import DatePickerField, make_modal, themed_entry


class FinancialDocsTabMixinMixin3:
    def _FinancialDocsTabMixin_build_financial_d_p2(self, frame):
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

    def _FinancialDocsTabMixin_add_financial_doc_p1(self, preset_path):
        file_path = preset_path
        if not file_path:
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
        return file_path

    def _FinancialDocsTabMixin_add_financial_doc_p2(self, file_path, FINANCIAL_DOC_CATEGORIES):
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
        return amt_var, cat_var, date_var, desc_var, dialog, file_name, sub_var
