from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.widgets import themed_entry


class ChecklistMixinMixin0:
    def _reload_checklists(self, keep: str | None = None) -> None:
        names = self.app.db.list_checklist_template_names()
        current = keep or self.checklist_menu.get()
        self.checklist_menu.configure(values=names)
        if current in names:
            self.checklist_menu.set(current)
        elif names:
            self.checklist_menu.set(names[0])
        self._load_checklist_items(self.checklist_menu.get())

    def _load_checklist_items(self, name: str) -> None:
        for frame, *_ in self._checklist_rows:
            frame.destroy()
        self._checklist_rows.clear()
        for entry in self.app.db.get_checklist_template_items(name):
            self._add_checklist_row(str(entry.get("item") or ""), str(entry.get("due_days") or 0))
        self._reconfigure_tab_scroll(self.tabs.tab("Business"))

    def _add_checklist_row(self, item: str, days: str) -> None:
        row = ctk.CTkFrame(self.checklist_scroll, fg_color="transparent")
        row.grid_columnconfigure((0, 1), weight=1, uniform="cl_row")
        item_var = ctk.StringVar(value=item)
        days_var = ctk.StringVar(value=days)
        themed_entry(row, textvariable=item_var).grid(row=0, column=0, sticky="ew")
        themed_entry(row, textvariable=days_var, width=90).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ctk.CTkButton(
            row,
            text="✕",
            width=36,
            fg_color="transparent",
            border_width=1,
            command=lambda f=row: self._remove_checklist_row(f),
        ).grid(row=0, column=2, padx=(6, 0))
        row.pack(fill="x", padx=6, pady=3)
        self._checklist_rows.append((row, item_var, days_var))

    def _remove_checklist_row(self, frame: ctk.CTkFrame) -> None:
        for index, (current, *_) in enumerate(self._checklist_rows):
            if current is frame:
                self._checklist_rows.pop(index)
                frame.destroy()
                self._reconfigure_tab_scroll(self.tabs.tab("Business"))
                return

    def _add_checklist_item(self) -> None:
        item = self._new_item_var.get().strip()
        days_raw = self._new_days_var.get().strip() or "0"
        if not item:
            self.feedback.error("Enter the checklist task text.")
            return
        try:
            days = int(days_raw)
        except ValueError:
            self.feedback.error("Days before expiry must be a number.")
            return
        self._add_checklist_row(item, str(days))
        self._new_item_var.set("")
        self._new_days_var.set("")
        self._reconfigure_tab_scroll(self.tabs.tab("Business"))

    def _save_checklist(self) -> None:
        name = self.checklist_menu.get().strip()
        rows: list[tuple[str, int]] = []
        for _, item_var, days_var in self._checklist_rows:
            item = item_var.get().strip()
            if not item:
                continue
            try:
                days = int(days_var.get().strip() or "0")
            except ValueError:
                self.feedback.error(f"Days for “{item[:30]}…” must be a number.")
                return
            rows.append((item, days))
        if not rows:
            self.feedback.error("Add at least one checklist item.")
            return
        try:
            self.app.db.set_checklist_template_items(name, rows)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self._reload_checklists(keep=name)
        self.feedback.success(f"Checklist “{name}” saved.")
        self.app.set_status(f"Renewal checklist “{name}” updated.")
        self._reconfigure_tab_scroll(self.tabs.tab("Business"))

    def _add_checklist_list(self) -> None:
        name = self._new_list_var.get().strip()
        if not name:
            self.feedback.error("Enter a name for the new checklist.")
            return
        try:
            self.app.db.add_checklist_template(name)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self._new_list_var.set("")
        self._reload_checklists(keep=name)
        self.feedback.success(f"Checklist “{name}” added — add items, then Save.")
