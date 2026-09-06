"""Document Hub — Portal Upload panel."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.services import file_ops
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE, TEXT_MUTED, TEXT_SUBTLE, WRAP_CARD
from skyadmin_pro.ui.views.document_hub.helpers import launch_portal, open_folder
from skyadmin_pro.ui.widgets import FeedbackLabel, themed_scrollable_frame


class PortalUploadPanel(ctk.CTkFrame):
    """Semi-auto uploader: open the portal and copy each Ready file's absolute path."""

    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._signature: tuple | None = None
        self._rows: list[ctk.CTkFrame] = []
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Ready to Upload — open portal & copy path",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            header,
            text="Open folder",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=lambda: open_folder(self.app.paths.ready_to_upload, parent=self.winfo_toplevel()),
        ).grid(row=0, column=1, sticky="e")

        card = ctk.CTkFrame(self, corner_radius=12)
        card.grid(row=1, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)
        desc = ctk.CTkLabel(
            card,
            text=(
                "Each Open Portal button saves a backup copy in "
                "Z_Archive_Backup/Portal_Backups, copies that file’s full local path "
                "to the clipboard, and opens the portal URL from Settings, "
                "so you can paste with Ctrl+V."
            ),
            wraplength=WRAP_CARD,
            justify="left",
            text_color=TEXT_MUTED,
            anchor="w",
        )
        desc.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        card.bind("<Configure>", lambda e: desc.configure(wraplength=max(300, e.width - 32)))

        self._scroll = themed_scrollable_frame(card)
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self._scroll.grid_columnconfigure(0, weight=1)
        self._empty = ctk.CTkLabel(
            self._scroll,
            text="No processed files in Ready to Upload yet.",
            text_color=TEXT_SUBTLE,
        )

        self.feedback = FeedbackLabel(card)
        self.feedback.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))

    def refresh(self) -> None:
        folder = self.app.paths.ready_to_upload
        files, signature = file_ops.list_files_with_signature(folder)
        self.render_files(files, signature)

    def render_files(self, files, signature) -> None:
        """Apply a background-scanned file list on the main thread."""
        if signature == self._signature:
            return
        self._signature = signature
        for row in self._rows:
            row.destroy()
        self._rows.clear()
        self._empty.grid_forget()
        if not files:
            self._empty.grid(row=0, column=0, padx=12, pady=16, sticky="w")
            return
        for index, path in enumerate(files):
            row = ctk.CTkFrame(self._scroll, fg_color="transparent")
            row.grid(row=index, column=0, sticky="ew", padx=4, pady=3)
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=path.name, anchor="w").grid(row=0, column=0, sticky="ew")
            ctk.CTkButton(
                row,
                text="Open Portal",
                width=120,
                command=lambda p=path: launch_portal(self.app, p, self.feedback),
            ).grid(row=0, column=1, padx=(8, 0))
            self._rows.append(row)
