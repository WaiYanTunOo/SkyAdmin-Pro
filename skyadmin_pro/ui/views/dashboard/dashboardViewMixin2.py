from __future__ import annotations

from .funcs import snap_fingerprint


class DashboardViewMixin2:
    def on_hide(self) -> None:
        self._visible = False
        try:
            from skyadmin_pro.ui.async_ui import cancel_pump

            cancel_pump(self)
        except Exception:
            pass
        self._snap_seq = int(getattr(self, "_snap_seq", 0)) + 1
        had_pending = bool(self._tree_refresh_after or self._detail_trees_after or self._timeline_after)
        self._cancel_deferred_refresh()
        self._cancel_detail_tree_build()
        if had_pending:
            self._trees_ready = False

    def mark_stale(self) -> None:
        """Force a full tree rebuild on the next refresh (e.g. after edits elsewhere)."""
        self._trees_ready = False
        self._snap_fingerprint = None

    def _cancel_deferred_refresh(self) -> None:
        for attr in ("_tree_refresh_after", "_detail_trees_after", "_timeline_after", "_timeline_resize_after"):
            after_id = getattr(self, attr, None)
            if after_id is not None:
                try:
                    self.after_cancel(after_id)
                except Exception:
                    pass
                setattr(self, attr, None)

    def refresh(self, *, force: bool = False) -> None:
        """Synchronous refresh (kept for tests / programmatic callers)."""
        self._cancel_deferred_refresh()
        if not getattr(self, "_header_extras_built", False):
            self._build_header_extras()
        if not self._detail_built:
            self._build_detail_trees()
        snap = self.app.db.dashboard_snapshot()
        self._apply_snapshot(snap, force=force)

    def refresh_async(self, *, force: bool = False) -> None:
        """Non-blocking entry for on_show/tab switches: snapshot off thread."""
        from skyadmin_pro.ui.async_ui import run_background

        self._cancel_deferred_refresh()
        self._snap_seq = int(getattr(self, "_snap_seq", 0)) + 1
        seq = self._snap_seq
        db = self.app.db
        try:
            self.app.set_status("Loading dashboard…")
        except Exception:
            pass

        def work():
            return db.dashboard_snapshot()

        def on_success(snap) -> None:
            if seq != getattr(self, "_snap_seq", 0) or not self.winfo_exists():
                return
            if not getattr(self, "_visible", True):
                # Hidden while loading: still cache cards, skip tree storms.
                try:
                    self._apply_stat_cards(snap)
                except Exception:
                    pass
                self._snap_fingerprint = snap_fingerprint(snap)
                return
            self._apply_snapshot(snap, force=force)
            try:
                self.app.set_status("Ready")
            except Exception:
                pass

        def on_error(msg: str) -> None:
            if seq != getattr(self, "_snap_seq", 0) or not self.winfo_exists():
                return
            try:
                self.app.set_status(f"Dashboard failed to load: {msg}")
            except Exception:
                pass

        run_background(self, work=work, on_success=on_success, on_error=on_error)
