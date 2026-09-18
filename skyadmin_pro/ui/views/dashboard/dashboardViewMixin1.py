from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CANVAS_BG, CANVAS_TEXT, CANVAS_VALUE_TEXT, TEXT_MUTED


class DashboardViewMixin1:
    def _progressive_detail_secondary(self) -> None:
        self._detail_build_after = None
        if not self.winfo_exists():
            return
        self._build_detail_trees_secondary()
        if self._detail_built:
            return
        self._detail_build_after = self.after(1, self._progressive_detail_heavy)

    def _progressive_detail_heavy(self) -> None:
        self._detail_build_after = None
        if not self.winfo_exists():
            return
        self._build_detail_trees_heavy()

    def _build_detail_trees_priority(self) -> None:
        """Above-the-fold trees: month panel, expiry, pending."""
        if getattr(self, "_detail_stage", 0) >= 1:
            return
        split = self._DashboardView_build_detail_trees_priori_p1()
        self._DashboardView_build_detail_trees_priori_p2(split)

    def _build_detail_trees_secondary(self) -> None:
        """Mid-weight payment / service trees."""
        if getattr(self, "_detail_stage", 0) >= 2:
            return
        overdue = self._DashboardView_build_detail_trees_second_p1()
        supplier_due = self._DashboardView_build_detail_trees_second_p2(overdue)
        self._DashboardView_build_detail_trees_second_p3(supplier_due)

    def _build_detail_trees_heavy(self) -> None:
        """Heaviest trees: incentive report and tax overview."""
        if self._detail_built:
            return
        report_card = self._DashboardView_build_detail_trees_heavy_p1()
        tax_overview = self._DashboardView_build_detail_trees_heavy_p2(report_card)
        self._DashboardView_build_detail_trees_heavy_p3(tax_overview)

    def _stat_card(self, master, column: int, label: str, value: str, command=None) -> ctk.CTkLabel:
        card = ctk.CTkFrame(master, corner_radius=14, height=110)
        if command:
            card.configure(cursor="hand2")
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 0))
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        title_lbl = ctk.CTkLabel(
            card,
            text=label,
            text_color=TEXT_MUTED,
            anchor="w",
            font=ctk.CTkFont(size=12),
            justify="left",
        )
        if command:
            title_lbl.configure(cursor="hand2")
        title_lbl.grid(row=0, column=0, sticky="new", padx=16, pady=(18, 0))
        from skyadmin_pro.ui.widgets import bind_wrap_label

        bind_wrap_label(title_lbl, card, pad=24)
        value_label = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=28, weight="bold"), anchor="w")
        if command:
            value_label.configure(cursor="hand2")
        value_label.grid(row=1, column=0, sticky="sw", padx=16, pady=(6, 16))

        if command:
            for widget in (card, title_lbl, value_label):
                widget.bind("<Button-1>", lambda e: command())

        return value_label

    def _draw_timeline(self, snap: dict | None = None) -> None:
        """Draw a bar-per-day expiry timeline for the next 45 days."""
        if not getattr(self, "_header_extras_built", False):
            return
        if snap is None:
            snap = getattr(self, "_last_snap", None)
        canvas = self.timeline_canvas
        canvas.delete("all")
        mode = ctk.get_appearance_mode()
        is_dark = mode == "Dark"
        bg = CANVAS_BG[1 if is_dark else 0]
        text_color = CANVAS_TEXT[1 if is_dark else 0]
        value_color = CANVAS_VALUE_TEXT[1 if is_dark else 0]
        canvas.configure(bg=bg)
        width = canvas.winfo_width()
        if width < 10:
            return
        bar_w, baseline, buckets, colors, height, max_count, x0 = self._DashboardView_draw_timeline_p1(
            canvas, snap, width, text_color
        )
        self._DashboardView_draw_timeline_p2(
            bar_w, baseline, buckets, canvas, colors, height, max_count, value_color, x0, width, text_color, mode
        )

    def on_show(self) -> None:
        self._visible = True
        # Clear any stale selection in the next-actions tree so returning from
        # a sub-view (e.g. Renewals) doesn't re-fire _next_selected and loop.
        if getattr(self, "next_tree", None) is not None:
            self.next_tree.tree.selection_remove(*self.next_tree.tree.selection())
        self._build_header_extras()
        self._schedule_detail_trees_progressive()
        self.refresh_async()
