from __future__ import annotations


class GlobalSearchDialogMixin1:
    def _on_return(self) -> None:
        hits = getattr(self, "_hits", None) or []
        query = self.search_var.get().strip()
        key = f"{self._filter.get()}\0{query}"
        if hits and key == self._last_query:
            self._navigate_and_close(hits[0])
            return
        self._run_search()

    def _run_search(self) -> None:
        from skyadmin_pro.ui.async_ui import run_background

        self._search_after = None
        query = self.search_var.get().strip()
        filter_type = self._filter.get()
        key = f"{filter_type}\0{query}"
        if key == self._last_query:
            return
        self._hits = []

        for widget in self._results_frame.winfo_children():
            widget.destroy()

        if not query or len(query) < 2:
            self._last_query = key
            self.feedback.info("Type at least 2 characters to search.")
            return

        self._search_seq = int(getattr(self, "_search_seq", 0)) + 1
        seq = self._search_seq
        self.feedback.info("Searching…")

        def work():
            return self._search_all(query, filter_type)

        def on_success(results) -> None:
            if seq != getattr(self, "_search_seq", 0):
                return
            try:
                if not self.winfo_exists():
                    return
            except Exception:
                return
            self._last_query = key
            self._render_results(results, query)

        def on_error(msg: str) -> None:
            if seq != getattr(self, "_search_seq", 0):
                return
            self._last_query = ""
            try:
                self.feedback.error(f"Search failed: {msg}")
            except Exception:
                pass

        run_background(self, work=work, on_success=on_success, on_error=on_error)
