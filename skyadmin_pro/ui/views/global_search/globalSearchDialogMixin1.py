from __future__ import annotations


class GlobalSearchDialogMixin1:
    def _run_search(self) -> None:
        from skyadmin_pro.ui.async_ui import run_background

        self._search_after = None
        query = self.search_var.get().strip()
        if query == self._last_query:
            return
        self._last_query = query

        # Clear previous results
        for widget in self._results_frame.winfo_children():
            widget.destroy()

        if not query:
            self.feedback.info("Type at least 2 characters to search.")
            return

        if len(query) < 2:
            self.feedback.info("Type at least 2 characters.")
            return

        filter_type = self._filter.get()
        self._search_seq = int(getattr(self, "_search_seq", 0)) + 1
        seq = self._search_seq
        self.feedback.info("Searching…")

        def work():
            return self._search_all(query, filter_type)

        def on_success(results) -> None:
            if seq != getattr(self, "_search_seq", 0):
                return
            try:
                exists = self.winfo_exists()
            except Exception:
                return
            if not exists:
                return
            self._render_results(results, query)

        def on_error(msg: str) -> None:
            if seq != getattr(self, "_search_seq", 0):
                return
            try:
                self.feedback.error(f"Search failed: {msg}")
            except Exception as e:
                import logging

                logging.error(f"UI Error: {e}")

        run_background(self, work=work, on_success=on_success, on_error=on_error)
