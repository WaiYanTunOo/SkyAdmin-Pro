"""Document Hub: Smart Renamer, Image-to-PDF, Agent Bundle, and Archive."""

from __future__ import annotations

import os
import threading
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from skyadmin_pro.config import (
    DOC_TYPE_INVOICE,
    DOC_TYPES_WITH_AMOUNT,
    DOC_TYPES_WITH_EXPIRY,
    DOCUMENT_TYPES,
    FOLDER_PORTAL_BACKUP,
    FOLDER_READY,
    FOLDER_STAGING,
    SETTING_PORTAL_URL,
)
from skyadmin_pro.services import file_ops
from skyadmin_pro.services.file_ops import open_in_file_manager
from skyadmin_pro.services.workflow import open_portal_and_copy_path
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE, TEXT_MUTED, TEXT_SUBTLE, WRAP_CARD
from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.widgets import DatePickerField, DropZone, FeedbackLabel, OrderedPathList, SelectableFileList


def _open_folder(path: Path, parent=None) -> None:
    try:
        file_ops.open_in_file_manager(path)
    except Exception as exc:
        messagebox.showerror(
            "SkyAdmin Pro",
            f"Could not open folder:\n{path}\n{exc}",
            parent=parent,
        )


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
            "Financial Docs",
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

        self.financial = FinancialDocsPanel(self.tabs.tab("Financial Docs"), self.app)
        self.financial.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    def refresh_all(self) -> None:
        if not hasattr(self, "portal"):
            return
        self.renamer.refresh()
        self.portal.refresh()
        self.archive.refresh()
        self.financial.refresh()

    def on_show(self) -> None:
        self._polling = True
        # Cancel any previously scheduled poll chain so re-selecting the view
        # cannot stack multiple concurrent polling loops.
        if self._poll_after is not None:
            try:
                self.after_cancel(self._poll_after)
            except Exception:
                pass
            self._poll_after = None
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
            command=lambda: _open_folder(self.app.paths.staging, parent=self.winfo_toplevel()),
        ).pack(side="left", padx=(8, 0))

        self.file_list = SelectableFileList(left, on_select=lambda _: self._update_preview())
        self.file_list.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        right = ctk.CTkFrame(self, corner_radius=12)
        right.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right, text="Client name", anchor="w").grid(row=0, column=0, sticky="w", padx=16, pady=(16, 4))
        self.client_var = ctk.StringVar()
        self._preview_after: str | None = None
        self.client_box = ctk.CTkComboBox(
            right,
            variable=self.client_var,
            values=[""],
            command=lambda _: self._schedule_preview(),
        )
        self.client_box.grid(row=1, column=0, sticky="ew", padx=16)
        self.client_var.trace_add("write", lambda *_: self._schedule_preview())

        ctk.CTkLabel(right, text="Document type", anchor="w").grid(row=2, column=0, sticky="w", padx=16, pady=(14, 4))
        self.type_menu = ctk.CTkOptionMenu(
            right,
            values=list(DOCUMENT_TYPES),
            command=self._on_type_change,
        )
        self.type_menu.grid(row=3, column=0, sticky="ew", padx=16)
        self.type_menu.set(DOCUMENT_TYPES[0])

        self.invoice_wrap = ctk.CTkFrame(right, fg_color="transparent")
        self.invoice_wrap.grid(row=4, column=0, sticky="ew", padx=16, pady=(14, 0))
        self.invoice_wrap.grid_columnconfigure(0, weight=1)
        self.invoice_sop = ctk.CTkCheckBox(
            self.invoice_wrap,
            text="SOP invoice naming: YYYYMM_Client_Invoice_INV…",
            command=self._update_preview,
        )
        self.invoice_sop.grid(row=0, column=0, sticky="w")

        self.expiry_wrap = ctk.CTkFrame(right, fg_color="transparent")
        self.expiry_wrap.grid(row=5, column=0, sticky="ew", padx=16, pady=(14, 0))
        self.expiry_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.expiry_wrap, text="Expiry date", anchor="w").grid(row=0, column=0, sticky="w")
        self.expiry_var = ctk.StringVar()
        DatePickerField(self.expiry_wrap, var=self.expiry_var).grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.expiry_var.trace_add("write", lambda *_: self._schedule_preview())

        self.amount_wrap = ctk.CTkFrame(right, fg_color="transparent")
        self.amount_wrap.grid(row=6, column=0, sticky="ew", padx=16, pady=(14, 0))
        self.amount_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.amount_wrap, text="Amount", anchor="w").grid(row=0, column=0, sticky="w")
        self.amount_var = ctk.StringVar()
        amount_entry = ctk.CTkEntry(
            self.amount_wrap,
            textvariable=self.amount_var,
            placeholder_text="e.g. 15000",
        )
        amount_entry.bind(
            "<FocusOut>",
            lambda _e: self.amount_var.set(file_ops.format_thousands(self.amount_var.get())),
        )
        amount_entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.amount_var.trace_add("write", lambda *_: self._schedule_preview())

        ctk.CTkLabel(right, text="New filename", anchor="w").grid(row=7, column=0, sticky="w", padx=16, pady=(16, 4))
        self.preview = ctk.CTkLabel(
            right,
            text="Select a file to preview the name.",
            anchor="w",
            wraplength=WRAP_CARD,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.preview.grid(row=8, column=0, sticky="ew", padx=16)
        # Keep preview readable on narrow windows — update wrap with card width.
        right.bind("<Configure>", lambda e: self.preview.configure(wraplength=max(220, e.width - 32)))

        self._busy = False
        self._rename_btn = ctk.CTkButton(
            right,
            text=f"Rename & move to {FOLDER_READY}",
            height=40,
            command=self._rename_and_move,
        )
        self._rename_btn.grid(row=9, column=0, sticky="ew", padx=16, pady=(18, 6))

        self.portal_button = ctk.CTkButton(
            right,
            text="Open portal & copy path",
            height=36,
            fg_color="transparent",
            border_width=1,
            state="disabled",
            command=self._open_last_portal,
        )
        self.portal_button.grid(row=10, column=0, sticky="ew", padx=16, pady=(0, 8))

        self.feedback = FeedbackLabel(right)
        self.feedback.grid(row=11, column=0, sticky="ew", padx=16, pady=(0, 16))

        self._last_ready: Path | None = None
        self._on_type_change(self.type_menu.get())

    def refresh(self, *, files_only: bool = False) -> None:
        folder = self.app.paths.staging
        files, signature = file_ops.list_files_with_signature(folder)
        if files_only and signature == self.file_list._signature:
            return
        self.file_list.set_files(files, signature=signature)
        if not files_only:
            names = self.app.db.list_client_names()
            current = self.client_var.get()
            self.client_box.configure(values=names or [""])
            if current:
                self.client_box.set(current)
        self._update_preview()

    def _on_type_change(self, choice: str) -> None:
        if choice == DOC_TYPE_INVOICE:
            self.invoice_wrap.grid()
        else:
            self.invoice_wrap.grid_remove()
        if choice in DOC_TYPES_WITH_EXPIRY:
            self.expiry_wrap.grid()
        else:
            self.expiry_wrap.grid_remove()
        if choice in DOC_TYPES_WITH_AMOUNT:
            self.amount_wrap.grid()
        else:
            self.amount_wrap.grid_remove()
        self._update_preview()

    def _invoice_name(self, client: str, suffix: str) -> str | None:
        client_id = self.app.db.client_id_by_name(client) or 0
        month_key = date.today().strftime("%Y%m")
        invoice_no = self.app.db.next_invoice_number(client_id, month_key)
        return file_ops.build_invoice_filename(client_name=client, suffix=suffix, invoice_no=invoice_no)

    def _preview_name(self) -> str | None:
        selected = self.file_list.selected
        client = self.client_var.get().strip()
        if selected is None or not client:
            return None
        doc_type = self.type_menu.get()
        if doc_type == DOC_TYPE_INVOICE and self.invoice_sop.get():
            return self._invoice_name(client, selected.suffix or ".pdf")
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

    def _schedule_preview(self) -> None:
        if self._preview_after is not None:
            try:
                self.after_cancel(self._preview_after)
            except Exception:
                pass
        self._preview_after = self.after(150, self._update_preview)

    def _update_preview(self) -> None:
        self._preview_after = None
        self.feedback.clear()
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
        if doc_type == DOC_TYPE_INVOICE and self.invoice_sop.get():
            client_id = self.app.db.get_or_create_client(client)
            month_key = date.today().strftime("%Y%m")
            invoice_no = self.app.db.next_invoice_number(client_id, month_key)
            new_name = file_ops.build_invoice_filename(
                client_name=client, suffix=selected.suffix or ".pdf", invoice_no=invoice_no
            )
            expiry_iso = None
            amount = None
        else:
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
        if self._busy:
            return
        self._busy = True
        self._rename_btn.configure(state="disabled")
        self.configure(cursor="watch")
        self.feedback.info("Moving file… please wait.")
        self.update_idletasks()

        def _worker():
            error: str | None = None
            success_name: str | None = None
            dest_path: Path | None = None
            try:
                dest = file_ops.move_file(selected, self.app.paths.ready_to_upload, new_name)
                dest_path = dest
                client_id = self.app.db.get_or_create_client(client)
                self.app.db.record_document(
                    client_id=client_id,
                    document_type=doc_type,
                    file_name=dest.name,
                    file_path=str(dest.resolve()),
                    expiry_date=expiry_iso,
                    amount=amount,
                )
                success_name = dest.name
            except OSError as exc:
                error = f"Could not move the file (in use or permission denied): {exc}"
            except Exception as exc:
                # Try to roll back the file move if DB failed.
                if dest_path is not None:
                    try:
                        file_ops.move_file(dest_path, selected.parent, selected.name)
                    except OSError:
                        pass
                error = f"Could not record the document: {exc}"

            def _done():
                if not self.winfo_exists():
                    return
                self._busy = False
                self.configure(cursor="")
                self._rename_btn.configure(state="normal")
                if error:
                    self.feedback.error(error)
                    return
                assert success_name is not None and dest_path is not None
                self.app.set_status(f"Moved to {FOLDER_READY}: {success_name}")
                self.feedback.success(f"Saved as {success_name}")
                self._last_ready = dest_path
                self.portal_button.configure(state="normal")
                self.refresh()

            try:
                self.after(0, _done)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _open_last_portal(self) -> None:
        if self._last_ready is None:
            self.feedback.error("Rename a file first.")
            return
        _launch_portal(self.app, self._last_ready, self.feedback)


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

        def _worker():
            error: str | None = None
            outputs: list[Path] | None = None
            try:
                outputs = file_ops.images_to_pdf(
                    images,
                    self.app.paths.staging,
                    combine=combine,
                )
            except Exception as exc:
                error = str(exc)

            def _done():
                if not self.winfo_exists():
                    return
                self._busy = False
                self.configure(cursor="")
                if error:
                    self.feedback.error(f"Conversion failed: {error}")
                    return
                assert outputs is not None
                names = ", ".join(path.name for path in outputs)
                extra = f" Skipped {skipped} non-image file(s)." if skipped else ""
                self.feedback.success(f"Saved to {FOLDER_STAGING}: {names}.{extra}")
                self.app.set_status(f"Converted {len(outputs)} PDF(s) into staging.")

            try:
                self.after(0, _done)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()


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
        ctk.CTkEntry(form, textvariable=self.output_var).grid(row=0, column=1, sticky="ew")

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

        def _worker():
            error: str | None = None
            output: Path | None = None
            try:
                output = file_ops.merge_pdfs(sources, target)
            except Exception as exc:
                error = str(exc)

            def _done():
                if not self.winfo_exists():
                    return
                self._busy = False
                self.configure(cursor="")
                self._merge_btn.configure(state="normal")
                if error:
                    self.feedback.error(f"Merge failed: {error}")
                    return
                assert output is not None
                self.feedback.success(f"Bundle saved as {output.name}")
                self.app.set_status(f"Merged {len(sources)} PDFs → {output.name}")

            try:
                self.after(0, _done)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()


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
            command=lambda: _open_folder(self.app.paths.ready_to_upload, parent=self.winfo_toplevel()),
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

        self._scroll = ctk.CTkScrollableFrame(card, fg_color=("gray92", "gray17"))
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
                command=lambda p=path: _launch_portal(self.app, p, self.feedback),
            ).grid(row=0, column=1, padx=(8, 0))
            self._rows.append(row)


def _launch_portal(app, path: Path, feedback: FeedbackLabel) -> None:
    url = (app.db.get_setting(SETTING_PORTAL_URL) or "").strip()
    if not url:
        feedback.error("Set the portal URL in Settings first.")
        return
    if not path.is_file():
        feedback.error("That file no longer exists. Refresh and try again.")
        return
    try:
        absolute = open_portal_and_copy_path(path, url, tk_window=app)
    except Exception as exc:
        feedback.error(f"Could not open the portal: {exc}")
        return
    try:
        backup = file_ops.backup_file(path, app.paths.archive / FOLDER_PORTAL_BACKUP)
    except OSError as exc:
        feedback.error(f"Portal opened, but the backup copy failed: {exc}")
        return
    feedback.success(f"Backup saved to {backup.name}. Portal opened — paste with Ctrl+V.\n{absolute}")
    app.set_status("Portal opened — file path on clipboard (backup saved).")


class ArchivePanel(ctk.CTkFrame):
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
            command=lambda: _open_folder(self.app.paths.archive, parent=self.winfo_toplevel()),
        ).pack(side="left", padx=(8, 0))

        self.feedback = FeedbackLabel(card)
        self.feedback.grid(row=6, column=0, sticky="ew", padx=20, pady=(0, 20))

        self.refresh()

    def refresh(self) -> None:
        ready, ready_sig = file_ops.list_files_with_signature(self.app.paths.ready_to_upload)
        staging, staging_sig = file_ops.list_files_with_signature(self.app.paths.staging)
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

    def _archive(self) -> None:
        if self._busy:
            return
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
        self._busy = True
        self._archive_btn.configure(state="disabled")
        self.configure(cursor="watch")
        self.feedback.info(f"Archiving {len(ready) + len(staging)} file(s)… please wait.")
        self.update_idletasks()

        def _worker():
            error: str | None = None
            result = None
            try:
                result = file_ops.archive_ready_and_clean_staging(self.app.paths)
            except Exception as exc:
                error = str(exc)

            def _done():
                if not self.winfo_exists():
                    return
                self._busy = False
                self.configure(cursor="")
                self._archive_btn.configure(state="normal")
                if error:
                    self.feedback.error(f"Archive failed: {error}")
                    return
                assert result is not None
                extra = ""
                if result.errors:
                    extra = " Some files could not be moved: " + "; ".join(result.errors)
                    self.feedback.error(f"Archived {result.total_moved} file(s) to {result.month_folder.name}.{extra}")
                else:
                    self.feedback.success(
                        f"Archived {len(result.moved_ready)} ready file(s) and "
                        f"{len(result.moved_staging)} staging file(s) to {result.month_folder.name}."
                    )
                self.app.set_status(f"Archived into {result.month_folder}")
                self.refresh()

            try:
                self.after(0, _done)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()


class FinancialDocsPanel(ctk.CTkFrame):
    """Cross-client search and browse for financial documents."""

    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_toolbar()
        self._build_treeview()
        self.refresh()

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
        bar.grid_columnconfigure(1, weight=3)
        bar.grid_columnconfigure(3, weight=1)
        bar.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(bar, text="Search:", font=("Segoe UI", 12)).grid(row=0, column=0, padx=(0, 4))
        self.search_var = ctk.StringVar()
        self._search_after: str | None = None
        self.search_entry = ctk.CTkEntry(
            bar, textvariable=self.search_var, placeholder_text="File name, description..."
        )
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.search_entry.bind("<Return>", lambda _: self._do_search())
        self.search_var.trace_add("write", lambda *_: self._debounced_search())

        ctk.CTkLabel(bar, text="Category:", font=("Segoe UI", 12)).grid(row=0, column=2, padx=(0, 4))
        from skyadmin_pro.config import FINANCIAL_DOC_CATEGORIES

        self.cat_var = ctk.StringVar(value="All")
        self.cat_menu = ctk.CTkOptionMenu(
            bar,
            variable=self.cat_var,
            values=["All"] + list(FINANCIAL_DOC_CATEGORIES),
            width=140,
        )
        self.cat_menu.grid(row=0, column=3, sticky="ew", padx=(0, 8))

        ctk.CTkLabel(bar, text="Client:", font=("Segoe UI", 12)).grid(row=0, column=4, padx=(0, 4))
        self.client_var = ctk.StringVar(value="All")
        self.client_menu = ctk.CTkOptionMenu(
            bar,
            variable=self.client_var,
            values=["All"],
            width=180,
        )
        self.client_menu.grid(row=0, column=5, sticky="ew", padx=(0, 8))

        ctk.CTkButton(bar, text="Search", width=70, command=self._do_search).grid(row=0, column=6, padx=(0, 4))
        ctk.CTkButton(
            bar, text="Clear", width=60, fg_color="transparent", border_width=1, command=self._clear_search
        ).grid(row=0, column=7, padx=(0, 4))
        ctk.CTkButton(bar, text="Open", width=60, command=self._open_selected).grid(row=0, column=8, padx=(0, 4))
        ctk.CTkButton(bar, text="Refresh", width=70, command=self.refresh).grid(row=0, column=9)

    def _build_treeview(self) -> None:
        from skyadmin_pro.ui.treeview import ThemedTreeview

        self.tree = ThemedTreeview(
            self,
            columns=(
                ("client", "Client", 160),
                ("date", "Date", 90),
                ("category", "Category", 120),
                ("filename", "File Name", 200),
                ("amount", "Amount", 90),
                ("description", "Description", 200),
            ),
            showheight=12,
            on_double_click=self._on_tree_double,
        )
        self.tree.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        summary_frame.grid(row=2, column=0, sticky="ew", padx=4, pady=(0, 4))
        self.summary_label = ctk.CTkLabel(summary_frame, text="", font=("Segoe UI", 11), text_color=TEXT_MUTED)
        self.summary_label.pack(side="left")

    def _populate_client_menu(self) -> None:
        clients = self.app.db.list_clients()
        names = sorted(c.get("name", "") for c in clients if c.get("name"))
        self.client_menu.configure(values=["All"] + names)
        # Preserve the current selection; only reset when it no longer exists.
        if self.client_var.get() not in ("All",) + tuple(names):
            self.client_var.set("All")

    def _debounced_search(self) -> None:
        if self._search_after is not None:
            try:
                self.after_cancel(self._search_after)
            except Exception:
                pass
        self._search_after = self.after(300, self._do_search)

    def _clear_search(self) -> None:
        if self._search_after is not None:
            try:
                self.after_cancel(self._search_after)
            except Exception:
                pass
            self._search_after = None
        self.search_var.set("")
        self.cat_var.set("All")
        self.client_var.set("All")
        self._do_search()

    def _on_tree_double(self, iid: str | None) -> None:
        if iid is not None:
            try:
                self.tree.tree.selection_set(iid)
            except Exception:
                pass
        self._open_selected()

    def refresh(self) -> None:
        self._populate_client_menu()
        self._do_search()

    def _do_search(self) -> None:
        keyword = self.search_var.get().strip()
        cat_filter = self.cat_var.get()
        client_filter = self.client_var.get()

        rows = self.app.db.search_financial_documents(keyword) if keyword else self.app.db.all_financial_documents()

        if cat_filter != "All":
            rows = [r for r in rows if r.get("category") == cat_filter]
        if client_filter != "All":
            rows = [r for r in rows if r.get("client_name") == client_filter]

        tree_rows = []
        tree_iids = []
        for doc in rows:
            tree_rows.append(
                (
                    doc.get("client_name", ""),
                    doc.get("doc_date") or "",
                    doc.get("category") or "",
                    doc.get("file_name") or "",
                    doc.get("amount") or "",
                    doc.get("description") or "",
                )
            )
            tree_iids.append(str(doc["id"]))
        self.tree.set_rows(tree_rows, iids=tree_iids)

        cats = {}
        for doc in rows:
            c = doc.get("category") or "Uncategorized"
            cats[c] = cats.get(c, 0) + 1
        parts = [f"{v} {k}" for k, v in sorted(cats.items())]
        self.summary_label.configure(
            text=f"{len(rows)} document(s) — {', '.join(parts)}" if parts else "No documents found"
        )

    def _open_selected(self) -> None:
        selected = self.tree.tree.selection()
        if not selected:
            return
        doc_id = int(selected[0])
        doc = self.app.db.get_financial_document(doc_id)
        if not doc:
            return
        path = doc.get("stored_path") or doc.get("file_path") or ""
        if not path or not os.path.exists(path):
            messagebox.showwarning("SkyAdmin Pro", f"File not found:\n{path}")
            return
        try:
            open_in_file_manager(Path(path))
        except (OSError, RuntimeError) as exc:
            messagebox.showerror("SkyAdmin Pro", f"Could not open file:\n{exc}")
