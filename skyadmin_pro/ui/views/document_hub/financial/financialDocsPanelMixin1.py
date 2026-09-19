from __future__ import annotations

import os
from pathlib import Path
from tkinter import messagebox

from skyadmin_pro.services.file_ops import open_in_file_manager


class FinancialDocsPanelMixin1:
    def _clear_search(self) -> None:
        if self._search_after is not None:
            try:
                self.after_cancel(self._search_after)
            except Exception as e:
                import logging

                logging.error(f"UI Error: {e}")
            self._search_after = None
        self.search_var.set("")
        self.cat_var.set("All")
        self.client_var.set("All")
        self._do_search()

    def _on_tree_double(self, iid: str | None) -> None:
        if iid is not None:
            try:
                self.tree.tree.selection_set(iid)
            except Exception as e:
                import logging

                logging.error(f"UI Error: {e}")
        self._open_selected()

    def refresh(self) -> None:
        self._populate_client_menu()
        self._do_search()

    def _do_search(self) -> None:
        self._search_after = None
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
        self.summary_label.configure(text=f"{len(rows)} document(s) — {', '.join(parts)}" if parts else "")

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
