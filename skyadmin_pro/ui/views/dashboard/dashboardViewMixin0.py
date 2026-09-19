from __future__ import annotations

import customtkinter as ctk

from .tabs import install_tabs


class DashboardViewMixin0:
    title = "Dashboard"
    subtitle = "Pending work and upcoming alerts. Jump cards open the single sidebar page for each tool."

    def build(self) -> None:
        self.body.grid_rowconfigure(0, weight=0)
        self.body.grid_rowconfigure(1, weight=1)
        self._tree_refresh_after: str | None = None
        self._detail_trees_after: str | None = None
        self._timeline_after: str | None = None
        self._visible = False
        self._trees_ready = False
        self._snap_fingerprint: tuple | None = None
        self._timeline_mode: str | None = None
        self._detail_built = False
        self._detail_stage = 0
        self._detail_build_after: str | None = None
        self._header_extras_built = False
        self._snap_seq = 0
        self._last_snap: dict | None = None

        self._header = ctk.CTkFrame(self.body, fg_color="transparent", height=1)
        self._header.grid(row=0, column=0, sticky="ew")
        self._header.grid_propagate(False)
        self._header.grid_columnconfigure(0, weight=1)

        # Tabs fill body; Today scrolls inside its tab. Incentive tree is outside scroll.
        self._detail = ctk.CTkFrame(self.body, fg_color="transparent")
        self._detail.grid(row=1, column=0, sticky="nsew")
        self._detail.grid_columnconfigure(0, weight=1)
        self._detail.grid_rowconfigure(0, weight=1)
        install_tabs(self)

    def _build_header_extras(self) -> None:
        """Timeline, workflow, and next-actions — deferred until first on_show()."""
        if self._header_extras_built:
            return
        workflow = self._DashboardView_build_header_extras_p1()
        next_card = self._DashboardView_build_header_extras_p2(workflow)
        self._DashboardView_build_header_extras_p3(next_card)

    def _build_detail_trees(self) -> None:
        """Build all detail trees synchronously (tests / force refresh)."""
        self._cancel_detail_tree_build()
        self._build_detail_trees_priority()
        self._build_detail_trees_secondary()
        self._build_detail_trees_heavy()

    def _cancel_detail_tree_build(self) -> None:
        after_id = getattr(self, "_detail_build_after", None)
        if after_id is not None:
            try:
                self.after_cancel(after_id)
            except Exception as e:
                import logging

                logging.error(f"UI Error: {e}")
            self._detail_build_after = None

    def _schedule_detail_trees_progressive(self) -> None:
        """Stage heavy trees across idle turns so first paint stays light."""
        if self._detail_built:
            return
        self._cancel_detail_tree_build()
        self._build_detail_trees_priority()
        if self._detail_built:
            return
        self._detail_build_after = self.after(1, self._progressive_detail_secondary)
