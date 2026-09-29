from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import NAV_COURIER, NAV_OFFICE_HUB, NAV_SUPPLIERS
from skyadmin_pro.ui.theme import (
    BADGE_CLIENT,
    BADGE_CONTACT,
    BADGE_DOCUMENT,
    BADGE_TASK,
    TEXT_MUTED,
)


class GlobalSearchDialogMixin3:
    def _render_results(self, results: list[dict], query: str) -> None:
        self._hits = list(results or [])
        if not results:
            self.feedback.info("No results found.")
            return

        self.feedback.success(f"{len(results)} result(s). Enter opens first · click to open.")
        badge_colors = {
            "Client": BADGE_CLIENT,
            "Pipeline": BADGE_TASK,
            "Expiry": ("#b45309", "#f59e0b"),
            "Document": BADGE_DOCUMENT,
            "Contact": BADGE_CONTACT,
            "Supplier": ("#0f766e", "#14b8a6"),
            "Courier": ("#7c3aed", "#a78bfa"),
        }

        for i, item in enumerate(results):
            row = ctk.CTkFrame(self._results_frame, fg_color="transparent", corner_radius=6)
            row.grid(row=i, column=0, sticky="ew", pady=2)
            row.grid_columnconfigure(1, weight=1)
            row.configure(cursor="hand2")
            ctk.CTkLabel(
                row,
                text=item["type"],
                width=72,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=badge_colors.get(item["type"], ("#6b7280", "#9ca3af")),
                text_color="white",
                corner_radius=4,
            ).grid(row=0, column=0, rowspan=2, padx=(0, 8))
            ctk.CTkLabel(row, text=item["title"], anchor="w", font=ctk.CTkFont(size=13, weight="bold")).grid(
                row=0, column=1, sticky="sw"
            )
            if item.get("subtitle"):
                ctk.CTkLabel(
                    row,
                    text=item["subtitle"],
                    anchor="w",
                    font=ctk.CTkFont(size=11),
                    text_color=TEXT_MUTED,
                ).grid(row=1, column=1, sticky="nw")

            def _navigate(_event, hit=item, owner=self) -> None:
                owner._navigate_and_close(hit)

            row.bind("<Button-1>", _navigate)
            for child in row.winfo_children():
                try:
                    child.bind("<Button-1>", _navigate)
                except Exception:
                    pass

    def _navigate_and_close(self, hit: dict) -> None:
        from skyadmin_pro.ui.views.dashboard.jumps import open_company, open_pipeline
        from skyadmin_pro.ui.views.dashboard.jumps_companies import open_expiry

        kind, value = hit.get("open") or (None, None)
        app = self.app
        try:
            if kind == "company" and value:
                open_company(app, str(value))
            elif kind == "pipeline" and value is not None:
                open_pipeline(app, str(value))
            elif kind == "expiry":
                open_expiry(app)
            elif kind == "office":
                app.show_view(NAV_OFFICE_HUB)
            elif kind == "suppliers":
                app.show_view(NAV_SUPPLIERS)
            elif kind == "courier":
                app.show_view(NAV_COURIER)
            else:
                app.show_view(hit.get("nav") or "dashboard")
        finally:
            self.destroy()
