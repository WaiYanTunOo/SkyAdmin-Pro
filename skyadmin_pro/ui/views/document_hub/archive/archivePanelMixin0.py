from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.services import file_ops
from skyadmin_pro.ui.theme import TEXT_MUTED, WRAP_CARD
from skyadmin_pro.ui.views.document_hub.helpers import open_folder
from skyadmin_pro.ui.widgets import FeedbackLabel


class ArchivePanelMixin0:
    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._archive_signature: tuple | None = None
        self._busy = False
        self.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(self, corner_radius=12)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="1-Click Archive & Clean",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 6))
        desc2 = ctk.CTkLabel(
            card,
            text=(
                "Moves every file in Ready to Upload into this month’s archive folder, "
                "then clears leftover files from Staging so the desk is empty. "
                "Nothing is deleted — staging leftovers are archived too."
            ),
            wraplength=WRAP_CARD,
            justify="left",
            text_color=TEXT_MUTED,
            anchor="w",
        )
        desc2.grid(row=1, column=0, sticky="ew", padx=20)
        card.bind("<Configure>", lambda e: desc2.configure(wraplength=max(300, e.width - 40)))

        self.ready_label = ctk.CTkLabel(card, text="", anchor="w")
        self.ready_label.grid(row=2, column=0, sticky="w", padx=20, pady=(16, 0))
        self.staging_label = ctk.CTkLabel(card, text="", anchor="w")
        self.staging_label.grid(row=3, column=0, sticky="w", padx=20, pady=(4, 0))
        self.folder_label = ctk.CTkLabel(
            card, text="", anchor="w", wraplength=WRAP_CARD, font=ctk.CTkFont(weight="bold")
        )
        self.folder_label.grid(row=4, column=0, sticky="w", padx=20, pady=(12, 0))
        card.bind("<Configure>", lambda e: self.folder_label.configure(wraplength=max(300, e.width - 40)), add="+")

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=5, column=0, sticky="ew", padx=20, pady=(18, 8))
        self._archive_btn = ctk.CTkButton(
            actions,
            text="Archive Ready files & clean Staging",
            height=40,
            command=self._archive,
        )
        self._archive_btn.pack(side="left")
        ctk.CTkButton(
            actions,
            text="Open archive folder",
            fg_color="transparent",
            border_width=1,
            command=lambda: open_folder(self.app.paths.archive, parent=self.winfo_toplevel()),
        ).pack(side="left", padx=(8, 0))

        self.feedback = FeedbackLabel(card)
        self.feedback.grid(row=6, column=0, sticky="ew", padx=20, pady=(0, 20))

        self.refresh()

    def refresh(self) -> None:
        ready, ready_sig = file_ops.list_files_with_signature(self.app.paths.ready_to_upload)
        staging, staging_sig = file_ops.list_files_with_signature(self.app.paths.staging)
        self.render_counts(ready, ready_sig, staging, staging_sig)

    def render_counts(self, ready, ready_sig, staging, staging_sig) -> None:
        """Apply a background-scanned file list on the main thread."""
        signature = (ready_sig, staging_sig)
        if signature == self._archive_signature:
            return
        self._archive_signature = signature
        folder = file_ops.month_archive_folder(self.app.paths.archive)
        self.ready_label.configure(
            text=f"Ready to Upload: {len(ready)} file(s)"
            + (f" — {', '.join(p.name for p in ready[:8])}" if ready else "")
        )
        self.staging_label.configure(
            text=f"Staging: {len(staging)} file(s)"
            + (f" — {', '.join(p.name for p in staging[:8])}" if staging else "")
        )
        self.folder_label.configure(text=f"Archive destination: {folder}")
