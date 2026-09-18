"""Clients & expiry tab — company list, workspace, and document expiry tracking."""

from __future__ import annotations


class ClientsExpiryPanelMixin2:
    def _debounced_search(self) -> None:
        # Wait for a pause in typing before hitting the database.
        if self._search_after is not None:
            try:
                self.after_cancel(self._search_after)
            except Exception:
                pass
        self._search_after = self.after(300, self._run_search)

    def _run_search(self) -> None:
        self._search_after = None
        self._page = 0
        self._refresh_client_table()

    def _clear_search(self) -> None:
        self.search_var.set("")
        self._run_search()
        try:
            self.search_entry.focus_set()
        except Exception:
            pass

    def _refresh_clients(self) -> None:
        """Group-filter menu legacy entry point (was missing → AttributeError)."""
        self._page = 0
        self._refresh_client_table()

    def _client_prev_page(self) -> None:
        if self._page > 0:
            self._page -= 1
            self._refresh_client_table()

    def _client_next_page(self) -> None:
        if self._has_more:
            self._page += 1
            self._refresh_client_table()

    def _on_client_page_size(self, value: str) -> None:
        try:
            self._page_size = max(50, int(value))
        except ValueError:
            self._page_size = 250
        self._page = 0
        self._refresh_client_table()

    def _update_client_pager(self, shown: int) -> None:
        label = f"Page {self._page + 1} · {shown} shown"
        if self._has_more:
            label += " · more…"
        try:
            self.client_page_label.configure(text=label)
            self.client_prev.configure(state="normal" if self._page > 0 else "disabled")
            self.client_next.configure(state="normal" if self._has_more else "disabled")
        except Exception:
            pass
