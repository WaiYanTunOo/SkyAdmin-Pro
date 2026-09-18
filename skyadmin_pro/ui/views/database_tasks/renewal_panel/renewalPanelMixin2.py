from __future__ import annotations

import customtkinter as ctk


class RenewalPanelMixin2:
    def _clear_checklist(self) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()
        self._checkboxes.clear()
        self.progress_label.configure(text="0 of 0")
        self.progress_bar.set(0)

    def _rebuild_checklist(self, items: list[dict]) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()
        self._checkboxes.clear()
        for row, item in enumerate(items):
            item_id = int(item["id"])
            done = bool(item.get("done"))
            checkbox = ctk.CTkCheckBox(
                self.scroll,
                text=item.get("item") or "",
                command=lambda iid=item_id: self._toggle(iid),
            )
            checkbox.grid(row=row, column=0, sticky="w", padx=8, pady=4)
            if done:
                checkbox.select()
            else:
                checkbox.deselect()
            self._checkboxes[item_id] = checkbox
        self._update_progress()

    def _update_progress(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            return
        done, total = self.app.db.renewal_checklist_progress(client_id, self._template)
        self.progress_label.configure(text=f"{done} of {total}")
        self.progress_bar.set(done / total if total else 0)

    def _toggle(self, item_id: int) -> None:
        checkbox = self._checkboxes.get(item_id)
        if checkbox is None:
            return
        try:
            self.app.db.set_renewal_item_done(item_id, bool(checkbox.get()))
        except Exception as exc:
            self.feedback.error(f"Could not update item: {exc}")
            return
        self._update_progress()

    def _reset_all(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            return
        try:
            items = self.app.db.list_renewal_checklist(client_id, self._template)
            for item in items:
                self.app.db.set_renewal_item_done(int(item["id"]), False)
            fresh = self.app.db.list_renewal_checklist(client_id, self._template)
        except Exception as exc:
            self.feedback.error(f"Could not reset checklist: {exc}")
            return
        self._rebuild_checklist(fresh)
        self.feedback.success("Renewal checklist reset — all items to do.")
