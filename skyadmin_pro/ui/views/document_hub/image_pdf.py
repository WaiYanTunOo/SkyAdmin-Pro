"""Document Hub — Image to PDF panel."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from skyadmin_pro.config import FOLDER_STAGING
from skyadmin_pro.services import file_ops
from skyadmin_pro.ui.widgets import DropZone, FeedbackLabel


class ImageToPdfPanel(ctk.CTkFrame):
    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._busy = False
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        dnd = bool(getattr(app, "dnd_available", False))
        hint = (
            "Drop JPG or PNG files here, or click to browse.\nEach image becomes a PDF in the staging folder."
            if dnd
            else "Click to choose JPG or PNG files.\nEach image becomes a PDF in the staging folder."
        )
        self.drop_zone = DropZone(
            self,
            title="Drop images to convert",
            subtitle=hint,
            on_files=self._convert,
            dnd_available=dnd,
        )
        self.drop_zone.grid(row=0, column=0, sticky="nsew")

        options = ctk.CTkFrame(self, fg_color="transparent")
        options.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.combine = ctk.CTkCheckBox(
            options,
            text="Combine all selected images into one PDF",
        )
        self.combine.pack(side="left")
        ctk.CTkButton(
            options,
            text="Browse images",
            width=130,
            command=self.drop_zone.browse,
        ).pack(side="left", padx=(16, 0))

        self.feedback = FeedbackLabel(self)
        self.feedback.grid(row=2, column=0, sticky="ew", pady=(10, 0))

    def _convert(self, paths: list[Path]) -> None:
        images = [path for path in paths if file_ops.is_image(path)]
        skipped = len(paths) - len(images)
        if not images:
            if skipped:
                self.feedback.error(f"Dropped {skipped} non-image file(s) — drop JPG/PNG files.")
            else:
                self.feedback.error("Drop or select JPG/PNG (or other image) files.")
            return
        if hasattr(self, "_busy") and self._busy:
            return
        self._busy = True
        self.configure(cursor="watch")
        self.feedback.info(f"Converting {len(images)} image(s)… please wait.")
        self.update_idletasks()
        combine = bool(self.combine.get())
        from skyadmin_pro.ui.async_ui import run_background

        def work() -> list[Path]:
            return file_ops.images_to_pdf(images, self.app.paths.staging, combine=combine)

        def on_success(outputs: list[Path]) -> None:
            names = ", ".join(path.name for path in outputs)
            extra = f" Skipped {skipped} non-image file(s)." if skipped else ""
            self.feedback.success(f"Saved to {FOLDER_STAGING}: {names}.{extra}")
            self.app.set_status(f"Converted {len(outputs)} PDF(s) into staging.")

        def finally_fn() -> None:
            self._busy = False
            self.configure(cursor="")

        run_background(
            self,
            work=work,
            on_success=on_success,
            on_error=lambda err: self.feedback.error(f"Conversion failed: {err}"),
            finally_fn=finally_fn,
        )
