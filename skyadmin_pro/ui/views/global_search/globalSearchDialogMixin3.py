from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import BADGE_CLIENT, BADGE_CONTACT, BADGE_DOCUMENT, BADGE_TASK, TEXT_MUTED


class GlobalSearchDialogMixin3:
    def _render_results(self, results: list[dict], query: str) -> None:
        if not results:
            self.feedback.info("No results found.")
            return

        self.feedback.success(f"{len(results)} result(s) found.")

        for i, item in enumerate(results):
            row = ctk.CTkFrame(self._results_frame, fg_color="transparent", corner_radius=6)
            row.grid(row=i, column=0, sticky="ew", pady=2)
            row.grid_columnconfigure(1, weight=1)
            row.configure(cursor="hand2")

            # Type badge — (light, dark) pairs; CTk resolves fg_color tuples
            # per appearance mode. Light variants are darkened for white text.
            badge_colors = {
                "Client": BADGE_CLIENT,
                "Task": BADGE_TASK,
                "Document": BADGE_DOCUMENT,
                "Contact": BADGE_CONTACT,
            }
            badge = ctk.CTkLabel(
                row,
                text=item["type"],
                width=70,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=badge_colors.get(item["type"], ("#6b7280", "#9ca3af")),
                text_color="white",
                corner_radius=4,
            )
            badge.grid(row=0, column=0, rowspan=2, padx=(0, 8))

            # Title
            ctk.CTkLabel(
                row,
                text=item["title"],
                anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
            ).grid(row=0, column=1, sticky="sw")

            # Subtitle
            if item["subtitle"]:
                ctk.CTkLabel(
                    row,
                    text=item["subtitle"],
                    anchor="w",
                    font=ctk.CTkFont(size=11),
                    text_color=TEXT_MUTED,
                ).grid(row=1, column=1, sticky="nw")

            # Click handler — bind the row and its children so clicks on
            # the badge/title/subtitle labels navigate too.
            nav = item["nav"]

            def _navigate(_event, n=nav, owner=self) -> None:
                owner._navigate_and_close(n)

            row.bind("<Button-1>", _navigate)
            for child in row.winfo_children():
                try:
                    child.bind("<Button-1>", _navigate)
                except Exception as e:
                    import logging

                    logging.error(f"UI Error: {e}")

    def _navigate_and_close(self, nav_key: str) -> None:
        self.app.show_view(nav_key)
        self.destroy()
