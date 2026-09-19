from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from skyadmin_pro.config import NOTEBOOK_ENTRY_TYPES
from skyadmin_pro.ui.canvas_scroll import CanvasScrollFrame
from skyadmin_pro.ui.debounce import debounced_after
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE, TEXT_MUTED, card_style_kwargs
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import themed_entry


class NotebookTabMixinMixin1:
    def _delete_note(self) -> None:
        if self._selected_note_id is None:
            self.feedback.error("Select a note first.")
            return
        if not messagebox.askyesno("Delete note", "Delete this notebook entry?", parent=self.winfo_toplevel()):
            return
        self.app.db.delete_notebook_entry(self._selected_note_id)
        self._new_note()
        self.feedback.success("Note deleted.")
        self._refresh_notes()

    def _NotebookTabMixin_build_notebook_tab_p1(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(
            parent,
            text="Office instructions and follow-ups — not client expiry dates.",
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(8, 0))

        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", pady=(8, 8))
        toolbar.grid_columnconfigure(0, weight=1)
        self.note_search_var = ctk.StringVar()
        themed_entry(toolbar, textvariable=self.note_search_var, placeholder_text="Search notebook…").grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        self.note_search_var.trace_add("write", debounced_after(self, self._refresh_notes))
        type_labels = ["All"] + [label for _key, label in NOTEBOOK_ENTRY_TYPES]
        self.note_type_menu = ctk.CTkOptionMenu(
            toolbar, values=type_labels, command=lambda _v: self._refresh_notes(), width=170
        )
        self.note_type_menu.grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Today", width=70, command=self._filter_notes_today).grid(
            row=0, column=2, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="This week", width=90, command=self._filter_notes_week).grid(
            row=0, column=3, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="New note", width=100, command=self._new_note).grid(row=0, column=4)

        self.notes_tree = ThemedTreeview(
            parent,
            columns=(
                ("date", "Date", 100),
                ("type", "Type", 130),
                ("title", "Title", 220),
                ("author", "From", 120),
                ("client", "Client", 140),
            ),
            on_select=self._on_note_select,
            showheight=10,
            table_id="office.notebook",
            db=self.app.db,
        )
        self.notes_tree.grid(row=2, column=0, sticky="nsew")

        scroll = CanvasScrollFrame(parent)
        scroll.grid(row=3, column=0, sticky="ew")
        scroll.content.grid_columnconfigure(0, weight=1)
        self._notebook_scroll = scroll
        form = ctk.CTkFrame(scroll.content, corner_radius=12, **card_style_kwargs())
        form.grid(row=0, column=0, sticky="ew", pady=(10, 8), padx=4)
        form.grid_columnconfigure(0, weight=1, uniform="note_col")
        form.grid_columnconfigure(1, weight=1, uniform="note_col")
        ctk.CTkLabel(form, text="Notebook entry", font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 8)
        )

        self.n_type = ctk.StringVar(value=NOTEBOOK_ENTRY_TYPES[-1][1])
        return form
