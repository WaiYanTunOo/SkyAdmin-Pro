"""Office Hub — notebook tab."""

from __future__ import annotations

from datetime import date, timedelta
from tkinter import messagebox

import customtkinter as ctk

from skyadmin_pro.config import NOTEBOOK_ENTRY_TYPES
from skyadmin_pro.ui.canvas_scroll import CanvasScrollFrame
from skyadmin_pro.ui.debounce import debounced_after
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import themed_entry


class NotebookTabMixin:
    def _build_notebook_tab(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        scroll = CanvasScrollFrame(parent)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.content.grid_columnconfigure(0, weight=1)
        self._notebook_scroll = scroll
        body = scroll.content

        toolbar = ctk.CTkFrame(body, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(8, 8))
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
            body,
            columns=(
                ("date", "Date", 100),
                ("type", "Type", 130),
                ("title", "Title", 220),
                ("author", "From", 120),
                ("client", "Client", 140),
            ),
            on_select=self._on_note_select,
            showheight=8,
        )
        self.notes_tree.grid(row=1, column=0, sticky="nsew")

        form = ctk.CTkFrame(body, corner_radius=12)
        form.grid(row=2, column=0, sticky="ew", pady=(10, 8))
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(form, text="Notebook entry", font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(12, 8)
        )

        self.n_type = ctk.StringVar(value=NOTEBOOK_ENTRY_TYPES[-1][1])
        self.n_title = ctk.StringVar()
        self.n_date = ctk.StringVar(value=date.today().isoformat())
        self.n_author = ctk.StringVar()
        self.n_client = ctk.StringVar()
        self.n_follow = ctk.StringVar()
        self.n_pinned = ctk.BooleanVar()

        note_fields = [
            ("Type", self.n_type, 1, 0, "menu"),
            ("Title", self.n_title, 1, 2, "entry"),
            ("Date", self.n_date, 2, 0, "entry"),
            ("Author / from", self.n_author, 2, 2, "entry"),
            ("Linked client", self.n_client, 3, 0, "entry"),
            ("Follow-up date", self.n_follow, 3, 2, "entry"),
        ]
        for label, var, row, col, kind in note_fields:
            ctk.CTkLabel(form, text=label, anchor="w").grid(row=row, column=col, sticky="w", padx=16, pady=4)
            if kind == "menu":
                ctk.CTkOptionMenu(form, variable=var, values=[lbl for _k, lbl in NOTEBOOK_ENTRY_TYPES], width=200).grid(
                    row=row, column=col + 1, sticky="w", padx=(0, 16), pady=4
                )
            else:
                themed_entry(form, textvariable=var).grid(row=row, column=col + 1, sticky="ew", padx=(0, 16), pady=4)

        ctk.CTkLabel(form, text="Body", anchor="w").grid(row=4, column=0, sticky="nw", padx=16, pady=4)
        self.n_body_box = ctk.CTkTextbox(form, height=120)
        self.n_body_box.grid(row=4, column=1, columnspan=3, sticky="ew", padx=(0, 16), pady=4)
        ctk.CTkCheckBox(form, text="Pin to top", variable=self.n_pinned).grid(row=5, column=1, sticky="w", pady=4)

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=6, column=0, columnspan=4, sticky="w", padx=16, pady=(4, 14))
        ctk.CTkButton(buttons, text="Save note", width=110, command=self._save_note).pack(side="left")
        ctk.CTkButton(
            buttons, text="Delete", width=90, fg_color="transparent", border_width=1, command=self._delete_note
        ).pack(side="left", padx=(8, 0))

        self._note_from_date: str | None = None
        self._note_to_date: str | None = None

    def _refresh_notes(self) -> None:
        if "Notebook" not in self._lazy_tabs:
            return
        type_label = self.note_type_menu.get()
        entry_type = None if type_label == "All" else self._notebook_type_key(type_label)
        rows = self.app.db.list_notebook_entries(
            query=self.note_search_var.get(),
            entry_type=entry_type,
            from_date=self._note_from_date,
            to_date=self._note_to_date,
        )
        tree_rows = [
            (
                row.get("entry_date") or "",
                self._notebook_type_label(row.get("entry_type") or "general"),
                row.get("title") or "",
                row.get("author") or "",
                row.get("client_name") or "",
            )
            for row in rows
        ]
        self.notes_tree.set_rows(
            tree_rows,
            iids=[str(r["id"]) for r in rows],
            empty_message="No notebook entries match this filter.",
        )
        if hasattr(self, "_notebook_scroll"):
            self._notebook_scroll._on_content_configure()

    def _filter_notes_today(self) -> None:
        today = date.today().isoformat()
        self._note_from_date = today
        self._note_to_date = today
        self._refresh_notes()

    def _filter_notes_week(self) -> None:
        today = date.today()
        start = today - timedelta(days=today.weekday())
        self._note_from_date = start.isoformat()
        self._note_to_date = today.isoformat()
        self._refresh_notes()

    def _on_note_select(self, iid: str | None) -> None:
        if not iid:
            return
        self._selected_note_id = int(iid)
        row = self.app.db.get_notebook_entry(self._selected_note_id)
        if not row:
            return
        self.n_type.set(self._notebook_type_label(row.get("entry_type") or "general"))
        self.n_title.set(row.get("title") or "")
        self.n_date.set(row.get("entry_date") or "")
        self.n_author.set(row.get("author") or "")
        self.n_client.set(row.get("client_name") or "")
        self.n_follow.set(row.get("follow_up_date") or "")
        self.n_pinned.set(bool(row.get("is_pinned")))
        self.n_body_box.delete("1.0", "end")
        self.n_body_box.insert("1.0", row.get("body") or "")

    def _new_note(self) -> None:
        self._selected_note_id = None
        self._note_from_date = None
        self._note_to_date = None
        self.n_type.set(NOTEBOOK_ENTRY_TYPES[0][1])
        self.n_title.set("")
        self.n_date.set(date.today().isoformat())
        self.n_author.set("")
        self.n_client.set("")
        self.n_follow.set("")
        self.n_pinned.set(False)
        self.n_body_box.delete("1.0", "end")

    def _save_note(self) -> None:
        type_key = self._notebook_type_key(self.n_type.get()) or "general"
        payload = {
            "entry_type": type_key,
            "title": self.n_title.get(),
            "body": self.n_body_box.get("1.0", "end").strip() or None,
            "entry_date": self.n_date.get().strip() or date.today().isoformat(),
            "author": self.n_author.get().strip() or None,
            "client_id": self._client_id(self.n_client.get()),
            "follow_up_date": self.n_follow.get().strip() or None,
            "is_pinned": self.n_pinned.get(),
        }
        try:
            if self._selected_note_id is None:
                self._selected_note_id = self.app.db.add_notebook_entry(**payload)
            else:
                self.app.db.update_notebook_entry(self._selected_note_id, **payload)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success("Notebook entry saved.")
        self._refresh_notes()

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
