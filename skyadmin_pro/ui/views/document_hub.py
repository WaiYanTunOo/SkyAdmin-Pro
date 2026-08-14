"""Document Hub: Smart Renamer, Image-to-PDF, Agent Bundle, and Archive."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from skyadmin_pro.config import (
    DOC_TYPES_WITH_AMOUNT,
    DOC_TYPES_WITH_EXPIRY,
    DOCUMENT_TYPES,
    FOLDER_READY,
    FOLDER_STAGING,
    SETTING_PORTAL_URL,
)
from skyadmin_pro.services import file_ops
from skyadmin_pro.services.workflow import open_portal_and_copy_path
from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.widgets import DropZone, FeedbackLabel, OrderedPathList, SelectableFileList


def _open_folder(path: Path) -> None:
    try:
        file_ops.open_in_file_manager(path)
    except Exception as exc:
        messagebox.showerror("SkyAdmin Pro", str(exc))


class DocumentHubView(BaseView):
    title = "Document Hub"
    subtitle = "Rename, convert, merge, and archive client documents."

    def build(self) -> None:
        self._polling = False
        self._poll_after: str | None = None
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=1)

        self.tabs = ctk.CTkTabview(self.body, command=self.refresh_all)
        self.tabs.grid(row=0, column=0, sticky="nsew")
        tab_names = (
            "Smart Renamer",
            "Image to PDF",
            "Agent Bundle",
            "Portal Upload",
            "Archive & Clean",
        )
        for name in tab_names:
            self.tabs.add(name)
            tab = self.tabs.tab(name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

        self.renamer = SmartRenamerPanel(self.tabs.tab("Smart Renamer"), self.app)
        self.renamer.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.converter = ImageToPdfPanel(self.tabs.tab("Image to PDF"), self.app)
        self.converter.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.merger = AgentBundlePanel(self.tabs.tab("Agent Bundle"), self.app)
        self.merger.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.portal = PortalUploadPanel(self.tabs.tab("Portal Upload"), self.app)
        self.portal.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.archive = ArchivePanel(self.tabs.tab("Archive & Clean"), self.app)
        self.archive.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    def refresh_all(self) -> None:
        if not hasattr(self, "portal"):
            return
        self.renamer.refresh()
        self.portal.refresh()
        self.archive.refresh()

    def on_show(self) -> None:
        self._polling = True
        self.refresh_all()
        self._poll()

    def on_hide(self) -> None:
        self._polling = False
        if self._poll_after is not None:
            try:
                self.after_cancel(self._poll_after)
            except Exception:
                pass
            self._poll_after = None

    def _poll(self) -> None:
        if not self._polling or not self.winfo_exists():
            return
        try:
            self.renamer.refresh(files_only=True)
            self.portal.refresh()
            self.archive.refresh()
        except Exception:
            pass
        if self._polling and self.winfo_exists():
            self._poll_after = self.after(2000, self._poll)


class SmartRenamerPanel(ctk.CTkFrame):
    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text="Staging files",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        ctk.CTkLabel(
            self,
            text="Rename details",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(16, 0), pady=(0, 8))

        left = ctk.CTkFrame(self, corner_radius=12)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(left, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        ctk.CTkButton(toolbar, text="Refresh", width=90, command=self.refresh).pack(
            side="left"
        )
        ctk.CTkButton(
            toolbar,
            text="Open folder",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=lambda: _open_folder(self.app.paths.staging),
        ).pack(side="left", padx=(8, 0))

        self.file_list = SelectableFileList(left, on_select=lambda _: self._update_preview())
        self.file_list.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        right = ctk.CTkFrame(self, corner_radius=12)
        right.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right, text="Client name", anchor="w").grid(
            row=0, column=0, sticky="w", padx=16, pady=(16, 4)
        )
        self.client_var = ctk.StringVar()
        self.client_box = ctk.CTkComboBox(
            right,
            variable=self.client_var,
            values=[""],
            command=lambda _: self._update_preview(),
        )
        self.client_box.grid(row=1, column=0, sticky="ew", padx=16)
        self.client_var.trace_add("write", lambda *_: self._update_preview())

        ctk.CTkLabel(right, text="Document type", anchor="w").grid(
            row=2, column=0, sticky="w", padx=16, pady=(14, 4)
        )
        self.type_menu = ctk.CTkOptionMenu(
            right,
            values=list(DOCUMENT_TYPES),
            command=self._on_type_change,
        )
        self.type_menu.grid(row=3, column=0, sticky="w", padx=16)
        self.type_menu.set(DOCUMENT_TYPES[0])

        self.expiry_wrap = ctk.CTkFrame(right, fg_color="transparent")
        self.expiry_wrap.grid(row=4, column=0, sticky="ew", padx=16, pady=(14, 0))
        self.expiry_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.expiry_wrap, text="Expiry date", anchor="w").grid(
            row=0, column=0, sticky="w"
        )
        self.expiry_var = ctk.StringVar()
        ctk.CTkEntry(
            self.expiry_wrap,
            textvariable=self.expiry_var,
            placeholder_text="YYYY-MM-DD or DD/MM/YYYY",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.expiry_var.trace_add("write", lambda *_: self._update_preview())

        self.amount_wrap = ctk.CTkFrame(right, fg_color="transparent")
        self.amount_wrap.grid(row=5, column=0, sticky="ew", padx=16, pady=(14, 0))
        self.amount_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.amount_wrap, text="Amount", anchor="w").grid(
            row=0, column=0, sticky="w"
        )
        self.amount_var = ctk.StringVar()
        ctk.CTkEntry(
            self.amount_wrap,
            textvariable=self.amount_var,
            placeholder_text="e.g. 15000",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.amount_var.trace_add("write", lambda *_: self._update_preview())

        ctk.CTkLabel(right, text="New filename", anchor="w").grid(
            row=6, column=0, sticky="w", padx=16, pady=(16, 4)
        )
        self.preview = ctk.CTkLabel(
            right,
            text="Select a file to preview the name.",
            anchor="w",
            wraplength=420,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.preview.grid(row=7, column=0, sticky="ew", padx=16)

        ctk.CTkButton(
            right,
            text=f"Rename & move to {FOLDER_READY}",
            height=40,
            command=self._rename_and_move,
        ).grid(row=8, column=0, sticky="ew", padx=16, pady=(18, 6))

        self.portal_button = ctk.CTkButton(
            right,
            text="Open portal & copy path",
            height=36,
            fg_color="transparent",
            border_width=1,
            state="disabled",
            command=self._open_last_portal,
        )
        self.portal_button.grid(row=9, column=0, sticky="ew", padx=16, pady=(0, 8))

        self.feedback = FeedbackLabel(right)
        self.feedback.grid(row=10, column=0, sticky="ew", padx=16, pady=(0, 16))

        self._last_ready: Path | None = None
        self._on_type_change(self.type_menu.get())

    def refresh(self, *, files_only: bool = False) -> None:
        folder = self.app.paths.staging
        files = file_ops.list_files(folder)
        self.file_list.set_files(files, signature=file_ops.file_signature(folder))
        if not files_only:
            names = self.app.db.list_client_names()
            current = self.client_var.get()
            self.client_box.configure(values=names or [""])
            if current:
                self.client_box.set(current)
        self._update_preview()

    def _on_type_change(self, choice: str) -> None:
        if choice in DOC_TYPES_WITH_EXPIRY:
            self.expiry_wrap.grid()
        else:
            self.expiry_wrap.grid_remove()
        if choice in DOC_TYPES_WITH_AMOUNT:
            self.amount_wrap.grid()
        else:
            self.amount_wrap.grid_remove()
        self._update_preview()

    def _preview_name(self) -> str | None:
        selected = self.file_list.selected
        client = self.client_var.get().strip()
        if selected is None or not client:
            return None
        doc_type = self.type_menu.get()
        expiry = None
        amount = None
        if doc_type in DOC_TYPES_WITH_EXPIRY:
            expiry = file_ops.parse_flexible_date(self.expiry_var.get())
        if doc_type in DOC_TYPES_WITH_AMOUNT and self.amount_var.get().strip():
            amount = file_ops.sanitize_amount(self.amount_var.get())
        return file_ops.build_smart_filename(
            client_name=client,
            document_type=doc_type,
            suffix=selected.suffix or ".pdf",
            expiry_iso=expiry,
            amount=amount,
        )

    def _update_preview(self) -> None:
        name = self._preview_name()
        if name:
            self.preview.configure(text=name)
        else:
            self.preview.configure(text="Select a file and enter a client name.")

    def _rename_and_move(self) -> None:
        selected = self.file_list.selected
        client = self.client_var.get().strip()
        if selected is None:
            self.feedback.error("Select a file in the staging folder.")
            return
        if not selected.exists():
            self.feedback.error("That file is no longer in staging. Refresh and try again.")
            self.refresh()
            return
        if not client:
            self.feedback.error("Enter a client name.")
            return

        doc_type = self.type_menu.get()
        expiry_iso = None
        amount = None
        if doc_type in DOC_TYPES_WITH_EXPIRY:
            expiry_iso = file_ops.parse_flexible_date(self.expiry_var.get())
            if not expiry_iso:
                self.feedback.error("Enter a valid expiry date (YYYY-MM-DD or DD/MM/YYYY).")
                return
        if doc_type in DOC_TYPES_WITH_AMOUNT:
            raw = self.amount_var.get().strip()
            if not raw:
                self.feedback.error("Enter an invoice amount.")
                return
            amount = file_ops.sanitize_amount(raw)

        new_name = file_ops.build_smart_filename(
            client_name=client,
            document_type=doc_type,
            suffix=selected.suffix or ".pdf",
            expiry_iso=expiry_iso,
            amount=amount,
        )
        try:
            dest = file_ops.move_file(selected, self.app.paths.ready_to_upload, new_name)
            client_id = self.app.db.get_or_create_client(client)
            self.app.db.record_document(
                client_id=client_id,
                document_type=doc_type,
                file_name=dest.name,
                file_path=str(dest.resolve()),
                expiry_date=expiry_iso,
                amount=amount,
            )
        except OSError as exc:
            self.feedback.error(f"Could not move the file: {exc}")
            return

        self.app.set_status(f"Moved to {FOLDER_READY}: {dest.name}")
        self.feedback.success(f"Saved as {dest.name}")
        self._last_ready = dest
        self.portal_button.configure(state="normal")
        self.refresh()

    def _open_last_portal(self) -> None:
        if self._last_ready is None:
            self.feedback.error("Rename a file first.")
            return
        _launch_portal(self.app, self._last_ready, self.feedback)


class ImageToPdfPanel(ctk.CTkFrame):
    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        dnd = bool(getattr(app, "dnd_available", False))
        hint = (
            "Drop JPG or PNG files here, or click to browse.\n"
            "Each image becomes a PDF in the staging folder."
            if dnd
            else "Click to choose JPG or PNG files.\n"
            "Each image becomes a PDF in the staging folder."
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
            self.feedback.error("Drop or select JPG/PNG (or other image) files.")
            return
        try:
            outputs = file_ops.images_to_pdf(
                images,
                self.app.paths.staging,
                combine=bool(self.combine.get()),
            )
        except Exception as exc:
            self.feedback.error(f"Conversion failed: {exc}")
            return

        names = ", ".join(path.name for path in outputs)
        extra = f" Skipped {skipped} non-image file(s)." if skipped else ""
        self.feedback.success(f"Saved to {FOLDER_STAGING}: {names}.{extra}")
        self.app.set_status(f"Converted {len(outputs)} PDF(s) into staging.")


class AgentBundlePanel(ctk.CTkFrame):
    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text="Merge PDFs into one agent bundle",
            font=ctk.CTkFont(size=15, weight="bold"),
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
        ctk.CTkEntry(form, textvariable=self.output_var).grid(row=0, column=1, sticky="ew")

        ctk.CTkLabel(form, text="Save to").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=(10, 0)
        )
        self.dest_menu = ctk.CTkOptionMenu(
            form, values=[FOLDER_READY, FOLDER_STAGING]
        )
        self.dest_menu.set(FOLDER_READY)
        self.dest_menu.grid(row=1, column=1, sticky="w", pady=(10, 0))

        ctk.CTkButton(
            self,
            text="Merge into one PDF",
            height=40,
            command=self._merge,
        ).grid(row=4, column=0, sticky="ew", pady=(16, 8))

        self.feedback = FeedbackLabel(self)
        self.feedback.grid(row=5, column=0, sticky="ew")

    def _add_pdfs(self) -> None:
        selections = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        pdfs = [Path(item) for item in selections if file_ops.is_pdf(Path(item))]
        if not pdfs:
            return
        self.path_list.add_paths(pdfs)

    def _merge(self) -> None:
        sources = list(self.path_list.paths)
        if not sources:
            self.feedback.error("Add at least one PDF file to merge.")
            return
        name = self.output_var.get().strip() or f"{date.today().strftime('%Y%m%d')}_AgentBundle.pdf"
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        dest_dir = (
            self.app.paths.ready_to_upload
            if self.dest_menu.get() == FOLDER_READY
            else self.app.paths.staging
        )
        try:
            output = file_ops.merge_pdfs(sources, dest_dir / name)
        except Exception as exc:
            self.feedback.error(f"Merge failed: {exc}")
            return
        self.feedback.success(f"Bundle saved as {output.name}")
        self.app.set_status(f"Merged {len(sources)} PDFs → {output.name}")


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
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            header,
            text="Open folder",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=lambda: _open_folder(self.app.paths.ready_to_upload),
        ).grid(row=0, column=1, sticky="e")

        card = ctk.CTkFrame(self, corner_radius=12)
        card.grid(row=1, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            card,
            text=(
                "Each Open Portal button copies that file’s full local path to the clipboard "
                "and opens the portal URL from Settings, so you can paste with Ctrl+V."
            ),
            wraplength=760,
            justify="left",
            text_color=("gray40", "gray70"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))

        self._scroll = ctk.CTkScrollableFrame(card, fg_color=("gray92", "gray17"))
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self._scroll.grid_columnconfigure(0, weight=1)
        self._empty = ctk.CTkLabel(
            self._scroll,
            text="No processed files in Ready to Upload yet.",
            text_color=("gray45", "gray65"),
        )

        self.feedback = FeedbackLabel(card)
        self.feedback.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))

    def refresh(self) -> None:
        folder = self.app.paths.ready_to_upload
        signature = file_ops.file_signature(folder)
        if signature == self._signature:
            return
        self._signature = signature
        files = file_ops.list_files(folder)
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
                command=lambda p=path: _launch_portal(self.app, p, self.feedback),
            ).grid(row=0, column=1, padx=(8, 0))
            self._rows.append(row)


def _launch_portal(app, path: Path, feedback: FeedbackLabel) -> None:
    url = app.db.get_setting(SETTING_PORTAL_URL)
    try:
        absolute = open_portal_and_copy_path(path, url, tk_window=app)
    except Exception as exc:
        feedback.error(str(exc))
        return
    feedback.success(f"Path copied. Portal opened — paste with Ctrl+V.\n{absolute}")
    app.set_status("Portal opened — file path on clipboard.")


class ArchivePanel(ctk.CTkFrame):
    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
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
        ctk.CTkLabel(
            card,
            text=(
                "Moves every file in Ready to Upload into this month’s archive folder, "
                "then clears leftover files from Staging so the desk is empty. "
                "Nothing is deleted — staging leftovers are archived too."
            ),
            wraplength=720,
            justify="left",
            text_color=("gray35", "gray70"),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=20)

        self.ready_label = ctk.CTkLabel(card, text="", anchor="w")
        self.ready_label.grid(row=2, column=0, sticky="w", padx=20, pady=(16, 0))
        self.staging_label = ctk.CTkLabel(card, text="", anchor="w")
        self.staging_label.grid(row=3, column=0, sticky="w", padx=20, pady=(4, 0))
        self.folder_label = ctk.CTkLabel(
            card, text="", anchor="w", wraplength=720, font=ctk.CTkFont(weight="bold")
        )
        self.folder_label.grid(row=4, column=0, sticky="w", padx=20, pady=(12, 0))

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=5, column=0, sticky="ew", padx=20, pady=(18, 8))
        ctk.CTkButton(
            actions,
            text="Archive Ready files & clean Staging",
            height=40,
            command=self._archive,
        ).pack(side="left")
        ctk.CTkButton(
            actions,
            text="Open archive folder",
            fg_color="transparent",
            border_width=1,
            command=lambda: _open_folder(self.app.paths.archive),
        ).pack(side="left", padx=(8, 0))

        self.feedback = FeedbackLabel(card)
        self.feedback.grid(row=6, column=0, sticky="ew", padx=20, pady=(0, 20))

        self.refresh()

    def refresh(self) -> None:
        ready = file_ops.list_files(self.app.paths.ready_to_upload)
        staging = file_ops.list_files(self.app.paths.staging)
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

    def _archive(self) -> None:
        self.refresh()
        ready = file_ops.list_files(self.app.paths.ready_to_upload)
        staging = file_ops.list_files(self.app.paths.staging)
        if not ready and not staging:
            self.feedback.info("Both folders are already empty.")
            return
        folder = file_ops.month_archive_folder(self.app.paths.archive)
        confirmed = messagebox.askyesno(
            "Archive & Clean",
            (
                f"Move {len(ready)} Ready-to-Upload file(s) and "
                f"{len(staging)} Staging file(s) into:\n\n{folder}\n\nContinue?"
            ),
            parent=self.winfo_toplevel(),
        )
        if not confirmed:
            return
        result = file_ops.archive_ready_and_clean_staging(self.app.paths)
        extra = ""
        if result.errors:
            extra = " Some files could not be moved: " + "; ".join(result.errors)
            self.feedback.error(
                f"Archived {result.total_moved} file(s) to {result.month_folder.name}.{extra}"
            )
        else:
            self.feedback.success(
                f"Archived {len(result.moved_ready)} ready file(s) and "
                f"{len(result.moved_staging)} staging file(s) to {result.month_folder.name}."
            )
        self.app.set_status(f"Archived into {result.month_folder}")
        self.refresh()
