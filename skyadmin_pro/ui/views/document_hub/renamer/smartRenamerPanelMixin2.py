from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.canvas_scroll import CanvasScrollFrame
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE
from skyadmin_pro.ui.views.document_hub.helpers import open_folder
from skyadmin_pro.ui.widgets import SelectableFileList


class SmartRenamerPanelMixin2:
    def _SmartRenamerPanel__init__p1(self, app):
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text="Staging files",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        ctk.CTkLabel(
            self,
            text="Rename details",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(16, 0), pady=(0, 8))

        left = ctk.CTkFrame(self, corner_radius=12)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(left, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        ctk.CTkButton(toolbar, text="Refresh", width=90, command=self.refresh).pack(side="left")
        ctk.CTkButton(
            toolbar,
            text="Open folder",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=lambda: open_folder(self.app.paths.staging, parent=self.winfo_toplevel()),
        ).pack(side="left", padx=(8, 0))

        self.file_list = SelectableFileList(left, on_select=lambda _: self._update_preview())
        self.file_list.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        right = ctk.CTkFrame(self, corner_radius=12)
        right.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        self._rename_scroll = CanvasScrollFrame(right)
        self._rename_scroll.grid(row=0, column=0, sticky="nsew")
        self._rename_scroll.content.grid_columnconfigure(0, weight=1)
        body = self._rename_scroll.content

        ctk.CTkLabel(body, text="Client name", anchor="w").grid(row=0, column=0, sticky="w", padx=16, pady=(16, 4))
        self.client_var = ctk.StringVar()
        self._preview_after: str | None = None
        return body, right
