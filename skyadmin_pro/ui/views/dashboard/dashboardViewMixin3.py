from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import STAT_CRITICAL, STAT_MUTED, STAT_SUCCESS, STAT_WARNING

from .funcs import snap_fingerprint


class DashboardViewMixin3:
    def _apply_snapshot(self, snap: dict, *, force: bool = False) -> None:
        fingerprint = snap_fingerprint(snap)
        self._last_snap = snap
        self._apply_stat_cards(snap)
        if getattr(self, "_detail_stage", 0) >= 1:
            self.month_panel.refresh()

        if not force and self._trees_ready and fingerprint == self._snap_fingerprint:
            # Data unchanged — but a theme switch still needs a timeline redraw
            # (tk.Canvas is outside the apply_form_theme walk).
            if self._timeline_mode == ctk.get_appearance_mode():
                return
            self._draw_timeline(snap)
            self._timeline_mode = ctk.get_appearance_mode()
            return

        self._snap_fingerprint = fingerprint
        self._trees_ready = False
        if self._detail_built:
            self._refresh_report()
        seq = int(getattr(self, "_snap_seq", 0))
        self._tree_refresh_after = self.after(100, lambda s=snap, q=seq: self._refresh_priority_trees(s, _seq=q))

    def _apply_stat_cards(self, snap: dict) -> None:
        counts = snap["counts"]
        pending_filings = snap["pending_filings"]
        revenue = snap["revenue"]
        vo_csh_expiring = snap["vo_csh_expiring"]

        self.card_pending.configure(text=str(counts["pending"]))
        self.card_done.configure(text=str(counts["completed_today"]))
        self.card_expiring.configure(text=str(counts["expiring"]))
        self.card_overdue.configure(text=str(counts["overdue"]))
        self.card_clients.configure(text=str(counts["clients"]))
        self.card_supplier.configure(text=str(counts["supplier_due"]))
        self.card_ongoing.configure(text=str(counts["ongoing"]))
        self.card_pending_filings.configure(text=str(pending_filings))
        self.card_revenue.configure(text=f"{revenue:,}")
        self.card_vo_csh.configure(text=str(vo_csh_expiring))

        if counts["expiring"]:
            self.card_expiring.configure(text_color=STAT_WARNING)
        else:
            self.card_expiring.configure(text_color=STAT_MUTED)
        if counts["overdue"]:
            self.card_overdue.configure(text_color=STAT_CRITICAL)
        else:
            self.card_overdue.configure(text_color=STAT_MUTED)
        if counts["supplier_due"]:
            self.card_supplier.configure(text_color=STAT_WARNING)
        else:
            self.card_supplier.configure(text_color=STAT_MUTED)
        if counts["ongoing"]:
            self.card_ongoing.configure(text_color=STAT_SUCCESS)
        else:
            self.card_ongoing.configure(text_color=STAT_MUTED)
        if pending_filings:
            self.card_pending_filings.configure(text_color=STAT_WARNING)
        else:
            self.card_pending_filings.configure(text_color=STAT_MUTED)
        if vo_csh_expiring:
            self.card_vo_csh.configure(text_color=STAT_WARNING)
        else:
            self.card_vo_csh.configure(text_color=STAT_MUTED)

    def _refresh_priority_trees(self, snap: dict, _seq: int | None = None) -> None:
        self._tree_refresh_after = None
        if _seq is not None and _seq != getattr(self, "_snap_seq", 0):
            return
        if not self._visible or not self.winfo_exists():
            return
        if not getattr(self, "_header_extras_built", False):
            self._build_header_extras()

        self._refresh_tax_overview(snap.get("accounting_clients"))
        if not self._visible:
            return
        seq = int(getattr(self, "_snap_seq", 0))
        self._detail_trees_after = self.after(80, lambda s=snap, q=seq: self._refresh_detail_trees(s, _seq=q))
