"""Clients & expiry tab — company list, workspace, and document expiry tracking."""

from __future__ import annotations


class ClientsExpiryPanelMixin3:
    def _refresh_client_table(self) -> None:
        from skyadmin_pro.ui.async_ui import run_background

        try:
            query = self.search_var.get()
        except Exception:
            query = ""
        try:
            group_filter = self._group_filter_var.get()
        except Exception:
            group_filter = "All"
        group_map = dict(getattr(self, "_group_map", {}))
        page, page_size = self._page, self._page_size

        self._table_seq += 1
        seq = self._table_seq
        db = self.app.db

        def work():
            if group_filter != "All":
                gid = group_map.get(group_filter)
                # Group subsets are small: filter in Python, then page.
                clients = db.search_clients(query)
                if gid is not None:
                    clients = [c for c in clients if c.get("group_id") == gid]
                window = clients[page * page_size : page * page_size + page_size + 1]
                return window
            return db.search_clients(query, limit=page_size + 1, offset=page * page_size)

        def on_success(clients) -> None:
            if seq != self._table_seq or not self.winfo_exists():
                return
            self._has_more = len(clients) > self._page_size
            shown = clients[: self._page_size]
            rows, iids, tags = [], [], []
            for item in shown:
                rows.append(
                    (
                        item.get("name") or "—",
                        item.get("contact_name") or "—",
                        item.get("email") or "—",
                        "Active" if item.get("status") != "inactive" else "Inactive",
                    )
                )
                iids.append(str(item["id"]))
                tags.append(("inactive",) if item.get("status") == "inactive" else ())
            self.client_tree.set_rows(rows, iids=iids, tags=tags, empty_message="No clients match this search.")
            self._update_client_pager(len(shown))

        def on_error(msg: str) -> None:
            if seq != self._table_seq or not self.winfo_exists():
                return
            self.feedback.error(f"Client search failed: {msg}")

        run_background(self, work=work, on_success=on_success, on_error=on_error)

    def _export_excel(self) -> None:
        view = self.app.get_view("database_tasks")
        if view is not None and hasattr(view, "_export_excel"):
            view._export_excel()

    def _selected_client_name(self) -> str:
        selected = self.client_tree.selected_values()
        return selected[0] if selected else ""
