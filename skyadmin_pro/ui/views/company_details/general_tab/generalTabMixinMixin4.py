from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import IMPORTANT_DOC_TYPES
from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import DatePickerField, themed_entry


class GeneralTabMixinMixin4:
    def _GeneralTabMixin_build_documents_p1(self, master):
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_rowconfigure(2, weight=0)
        ctk.CTkLabel(
            frame,
            text="Important documents",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        self.doc_tree = ThemedTreeview(
            frame,
            columns=(
                ("type", "Document", 170),
                ("file", "File", 170),
                ("expiry", "Expiry", 95),
                ("added", "Added", 120),
            ),
            on_double_click=self._edit_document,
            table_id="company.documents",
            db=self.app.db,
        )
        self.doc_tree.tree.configure(height=5)
        self.doc_tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))

        form = ctk.CTkFrame(frame, fg_color="transparent")
        form.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        form.grid_columnconfigure((0, 1, 2), weight=1)

        self.document_status_label = ctk.CTkLabel(form, text="New document record", text_color=TEXT_MUTED)
        self.document_status_label.grid(row=0, column=0, columnspan=3, sticky="w", pady=(4, 6))

        ctk.CTkLabel(form, text="Document type").grid(row=1, column=0, sticky="w", pady=(2, 2))
        self.doc_type = ctk.CTkOptionMenu(form, values=list(IMPORTANT_DOC_TYPES))
        self.doc_type.set(IMPORTANT_DOC_TYPES[0])
        self.doc_type.grid(row=2, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkLabel(form, text="Expiry date (optional)").grid(row=1, column=1, sticky="w", pady=(2, 2))
        self.doc_expiry = ctk.StringVar()
        DatePickerField(form, var=self.doc_expiry).grid(row=2, column=1, sticky="ew", padx=(0, 6))

        ctk.CTkLabel(form, text="File (pick or type)").grid(row=1, column=2, sticky="w", pady=(2, 2))
        file_row = ctk.CTkFrame(form, fg_color="transparent")
        file_row.grid(row=2, column=2, sticky="ew", padx=(0, 6))
        file_row.grid_columnconfigure(0, weight=1)
        self.doc_file = ctk.StringVar()
        self.doc_path = ctk.StringVar()
        themed_entry(file_row, textvariable=self.doc_file).grid(row=0, column=0, sticky="ew")
        return file_row, form, frame

    def _GeneralTabMixin_build_documents_p2(self, file_row, form):
        ctk.CTkButton(
            file_row,
            text="Pick file…",
            width=90,
            command=self._pick_document_file,
        ).grid(row=0, column=1, padx=(6, 0))

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        buttons.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(buttons, text="Save document", command=self._save_document).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        self.cancel_doc_btn = ctk.CTkButton(
            buttons,
            text="Cancel",
            fg_color="transparent",
            border_width=1,
            command=self._cancel_document_edit,
        )
        self.cancel_doc_btn.grid(row=0, column=1, sticky="ew", padx=(2, 2))
        ctk.CTkButton(
            buttons,
            text="Delete selected",
            fg_color="transparent",
            border_width=1,
            command=self._delete_document,
        ).grid(row=0, column=2, sticky="ew", padx=(4, 0))
