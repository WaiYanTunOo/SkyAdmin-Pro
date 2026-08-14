"""Reusable CustomTkinter widgets for Document Hub."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import customtkinter as ctk

from skyadmin_pro.ui.dnd import enable_drop


class FeedbackLabel(ctk.CTkLabel):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, text="", anchor="w", wraplength=760, **kwargs)

    def success(self, message: str) -> None:
        self.configure(text=message, text_color=("#15803d", "#4ade80"))

    def error(self, message: str) -> None:
        self.configure(text=message, text_color=("#b91c1c", "#f87171"))

    def info(self, message: str) -> None:
        self.configure(text=message, text_color=("gray40", "gray70"))

    def clear(self) -> None:
        self.configure(text="")


class SelectableFileList(ctk.CTkFrame):
    """Single-select list of files in a folder, rebuilt only when contents change."""

    def __init__(
        self,
        master,
        *,
        on_select: Callable[[Path | None], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_select = on_select
        self._signature: tuple | None = None
        self._buttons: list[ctk.CTkButton] = []
        self.selected: Path | None = None
        self.files: list[Path] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=("gray92", "gray17"))
        self._scroll.grid(row=0, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)
        self._empty = ctk.CTkLabel(
            self._scroll,
            text="No files in this folder.",
            text_color=("gray45", "gray65"),
        )

    def set_files(self, files: list[Path], signature: tuple | None = None) -> None:
        if signature is not None and signature == self._signature:
            return
        previous = self.selected.name if self.selected else None
        self._signature = signature
        self.files = list(files)
        for button in self._buttons:
            button.destroy()
        self._buttons.clear()
        self._empty.grid_forget()

        if not files:
            self.selected = None
            self._empty.grid(row=0, column=0, padx=12, pady=16, sticky="w")
            if self._on_select:
                self._on_select(None)
            return

        restored: Path | None = None
        for index, path in enumerate(files):
            button = ctk.CTkButton(
                self._scroll,
                text=path.name,
                anchor="w",
                height=32,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray25"),
                command=lambda p=path: self.select(p),
            )
            button.grid(row=index, column=0, sticky="ew", padx=4, pady=2)
            self._buttons.append(button)
            if previous and path.name == previous:
                restored = path

        self.select(restored or files[0], notify=True)

    def select(self, path: Path | None, notify: bool = True) -> None:
        self.selected = path
        for button, file_path in zip(self._buttons, self.files):
            if path is not None and file_path == path:
                button.configure(fg_color=("gray75", "gray30"))
            else:
                button.configure(fg_color="transparent")
        if notify and self._on_select:
            self._on_select(path)


class OrderedPathList(ctk.CTkFrame):
    """Multi-file list with remove / move up / move down for the PDF merger."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.paths: list[Path] = []
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=("gray92", "gray17"))
        self._scroll.grid(row=0, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(1, weight=1)

    def add_paths(self, paths: list[Path]) -> None:
        existing = {item.resolve() for item in self.paths}
        for path in paths:
            if path.resolve() not in existing:
                self.paths.append(path)
                existing.add(path.resolve())
        self._redraw()

    def clear(self) -> None:
        self.paths.clear()
        self._redraw()

    def _move(self, index: int, delta: int) -> None:
        target = index + delta
        if 0 <= target < len(self.paths):
            self.paths[index], self.paths[target] = self.paths[target], self.paths[index]
            self._redraw()

    def _remove(self, index: int) -> None:
        if 0 <= index < len(self.paths):
            self.paths.pop(index)
            self._redraw()

    def _redraw(self) -> None:
        for child in self._scroll.winfo_children():
            child.destroy()
        if not self.paths:
            ctk.CTkLabel(
                self._scroll,
                text="No PDFs added yet.",
                text_color=("gray45", "gray65"),
            ).grid(row=0, column=0, columnspan=4, padx=12, pady=16, sticky="w")
            return
        for index, path in enumerate(self.paths):
            ctk.CTkLabel(
                self._scroll,
                text=f"{index + 1}.",
                width=28,
                anchor="e",
            ).grid(row=index, column=0, padx=(8, 4), pady=4)
            ctk.CTkLabel(self._scroll, text=path.name, anchor="w").grid(
                row=index, column=1, sticky="ew", padx=4, pady=4
            )
            ctk.CTkButton(
                self._scroll, text="Up", width=48, command=lambda i=index: self._move(i, -1)
            ).grid(row=index, column=2, padx=2, pady=4)
            ctk.CTkButton(
                self._scroll, text="Down", width=56, command=lambda i=index: self._move(i, 1)
            ).grid(row=index, column=3, padx=2, pady=4)
            ctk.CTkButton(
                self._scroll,
                text="Remove",
                width=72,
                fg_color="transparent",
                border_width=1,
                command=lambda i=index: self._remove(i),
            ).grid(row=index, column=4, padx=(2, 8), pady=4)


class DropZone(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        title: str,
        subtitle: str,
        on_files: Callable[[list[Path]], None],
        dnd_available: bool,
        **kwargs,
    ) -> None:
        super().__init__(master, corner_radius=12, border_width=2, **kwargs)
        self._on_files = on_files
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.grid(row=0, column=0, padx=24, pady=28)
        ctk.CTkLabel(inner, text=title, font=ctk.CTkFont(size=16, weight="bold")).pack()
        ctk.CTkLabel(
            inner,
            text=subtitle,
            text_color=("gray40", "gray70"),
            justify="center",
        ).pack(pady=(6, 0))

        for widget in (self, inner):
            widget.bind("<Button-1>", self._on_click)
        self._bind_clicks(inner)
        enable_drop(self, self._on_files, dnd_available)
        enable_drop(inner, self._on_files, dnd_available)

    def browse(self) -> None:
        self._on_click()

    def _bind_clicks(self, widget) -> None:
        widget.bind("<Button-1>", self._on_click)
        for child in widget.winfo_children():
            self._bind_clicks(child)

    def _on_click(self, _event=None) -> None:
        from tkinter import filedialog

        selections = filedialog.askopenfilenames(
            title="Select images",
            filetypes=[
                ("Images", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff"),
                ("All files", "*.*"),
            ],
        )
        if selections:
            self._on_files([Path(item) for item in selections])
