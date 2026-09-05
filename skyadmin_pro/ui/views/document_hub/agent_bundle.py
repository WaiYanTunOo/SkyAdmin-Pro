"""Document Hub — Agent Bundle panel."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from skyadmin_pro.config import FOLDER_READY, FOLDER_STAGING
from skyadmin_pro.services import file_ops
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE
from skyadmin_pro.ui.widgets import FeedbackLabel, OrderedPathList, themed_entry


class AgentBundlePanel(ctk.CTkFrame):
    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._busy = False
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text="Merge PDFs into one agent bundle",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.path_list = OrderedPathList(self)
        self.path_list.grid(row=1, column=0, sticky="nsew")

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        ctk.CTkButton(controls, text="Add PDFs", command=self._add_pdfs).pack(side="left")
        ctk.CTkButton(
            controls,
            text="Clear list",
            fg_color="transparent",
            border_width=1,
            command=self.path_list.clear,
        ).pack(side="left", padx=(8, 0))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="Output name").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.output_var = ctk.StringVar(value=f"{date.today().strftime('%Y%m%d')}_AgentBundle.pdf")
        themed_entry(form, textvariable=self.output_var).grid(row=0, column=1, sticky="ew")

        ctk.CTkLabel(form, text="Save to").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(10, 0))
        self.dest_menu = ctk.CTkOptionMenu(form, values=[FOLDER_READY, FOLDER_STAGING])
        self.dest_menu.set(FOLDER_READY)
        self.dest_menu.grid(row=1, column=1, sticky="w", pady=(10, 0))

        self._merge_btn = ctk.CTkButton(
            self,
            text="Merge into one PDF",
            height=40,
            command=self._merge,
        )
        self._merge_btn.grid(row=4, column=0, sticky="ew", pady=(16, 8))

        self.feedback = FeedbackLabel(self)
        self.feedback.grid(row=5, column=0, sticky="ew")

    def _add_pdfs(self) -> None:
        selections = filedialog.askopenfilenames(
            parent=self.winfo_toplevel(),
            title="Select PDF files",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not selections:
            return
        if isinstance(selections, str):
            selections = self.tk.splitlist(selections)
        pdfs = [Path(item) for item in selections if file_ops.is_pdf(Path(item))]
        skipped = len(selections) - len(pdfs)
        if not pdfs:
            if skipped:
                self.feedback.error(f"Skipped {skipped} non-PDF file(s) — only PDFs can be merged.")
            return
        self.path_list.add_paths(pdfs)
        if skipped:
            self.feedback.info(f"Added {len(pdfs)} PDF(s), skipped {skipped} non-PDF file(s).")

    def _merge(self) -> None:
        if self._busy:
            return
        sources = list(self.path_list.paths)
        if not sources:
            self.feedback.error("Add at least one PDF file to merge.")
            return
        name = self.output_var.get().strip() or f"{date.today().strftime('%Y%m%d')}_AgentBundle.pdf"
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        dest_dir = self.app.paths.ready_to_upload if self.dest_menu.get() == FOLDER_READY else self.app.paths.staging
        target = dest_dir / name
        self._busy = True
        self._merge_btn.configure(state="disabled")
        self.configure(cursor="watch")
        self.feedback.info(f"Merging {len(sources)} PDF(s)… please wait.")
        self.update_idletasks()
        from skyadmin_pro.ui.async_ui import run_background

        def work() -> Path:
            return file_ops.merge_pdfs(sources, target)

        def on_success(output: Path) -> None:
            self.feedback.success(f"Bundle saved as {output.name}")
            self.app.set_status(f"Merged {len(sources)} PDFs → {output.name}")

        def finally_fn() -> None:
            self._busy = False
            self.configure(cursor="")
            self._merge_btn.configure(state="normal")

        run_background(
            self,
            work=work,
            on_success=on_success,
            on_error=lambda err: self.feedback.error(f"Merge failed: {err}"),
            finally_fn=finally_fn,
        )
