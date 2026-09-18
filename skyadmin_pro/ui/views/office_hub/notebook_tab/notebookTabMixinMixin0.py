from __future__ import annotations

from datetime import date, timedelta

import customtkinter as ctk

from skyadmin_pro.config import NOTEBOOK_ENTRY_TYPES


class NotebookTabMixinMixin0:
    def _build_notebook_tab(self, parent: ctk.CTkFrame) -> None:
        form = self._NotebookTabMixin_build_notebook_tab_p1(parent)
        self._NotebookTabMixin_build_notebook_tab_p2(form)

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
