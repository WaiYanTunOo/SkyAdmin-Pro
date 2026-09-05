"""Document Hub — Smart Renamer panel."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import customtkinter as ctk

from skyadmin_pro.config import (
    DOC_TYPE_INVOICE,
    DOC_TYPES_WITH_AMOUNT,
    DOC_TYPES_WITH_EXPIRY,
    DOCUMENT_TYPES,
    FOLDER_READY,
)
from skyadmin_pro.services import file_ops
from skyadmin_pro.ui.canvas_scroll import CanvasScrollFrame
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE, WRAP_CARD
from skyadmin_pro.ui.views.document_hub.helpers import launch_portal, open_folder
from skyadmin_pro.ui.widgets import DatePickerField, FeedbackLabel, SelectableFileList, themed_entry


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
        self.client_box = ctk.CTkComboBox(
            body,
            variable=self.client_var,
            values=[""],
            command=lambda _: self._schedule_preview(),
        )
        self.client_box.grid(row=1, column=0, sticky="ew", padx=16)
        self.client_var.trace_add("write", lambda *_: self._schedule_preview())

        ctk.CTkLabel(body, text="Document type", anchor="w").grid(row=2, column=0, sticky="w", padx=16, pady=(14, 4))
        self.type_menu = ctk.CTkOptionMenu(
            body,
            values=list(DOCUMENT_TYPES),
            command=self._on_type_change,
        )
        self.type_menu.grid(row=3, column=0, sticky="ew", padx=16)
        self.type_menu.set(DOCUMENT_TYPES[0])

        self.invoice_wrap = ctk.CTkFrame(body, fg_color="transparent")
        self.invoice_wrap.grid(row=4, column=0, sticky="ew", padx=16, pady=(14, 0))
        self.invoice_wrap.grid_columnconfigure(0, weight=1)
        self.invoice_sop = ctk.CTkCheckBox(
            self.invoice_wrap,
            text="SOP invoice naming: YYYYMM_Client_Invoice_INV…",
            command=self._update_preview,
        )
        self.invoice_sop.grid(row=0, column=0, sticky="w")

        self.expiry_wrap = ctk.CTkFrame(body, fg_color="transparent")
        self.expiry_wrap.grid(row=5, column=0, sticky="ew", padx=16, pady=(14, 0))
        self.expiry_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.expiry_wrap, text="Expiry date", anchor="w").grid(row=0, column=0, sticky="w")
        self.expiry_var = ctk.StringVar()
        DatePickerField(self.expiry_wrap, var=self.expiry_var).grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.expiry_var.trace_add("write", lambda *_: self._schedule_preview())

        self.amount_wrap = ctk.CTkFrame(body, fg_color="transparent")
        self.amount_wrap.grid(row=6, column=0, sticky="ew", padx=16, pady=(14, 0))
        self.amount_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.amount_wrap, text="Amount", anchor="w").grid(row=0, column=0, sticky="w")
        self.amount_var = ctk.StringVar()
        amount_entry = themed_entry(
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

        ctk.CTkLabel(body, text="New filename", anchor="w").grid(row=7, column=0, sticky="w", padx=16, pady=(16, 4))
        self.preview = ctk.CTkLabel(
            body,
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
            body,
            text=f"Rename & move to {FOLDER_READY}",
            height=40,
            command=self._rename_and_move,
        )
        self._rename_btn.grid(row=9, column=0, sticky="ew", padx=16, pady=(18, 6))

        self.portal_button = ctk.CTkButton(
            body,
            text="Open portal & copy path",
            height=36,
            fg_color="transparent",
            border_width=1,
            state="disabled",
            command=self._open_last_portal,
        )
        self.portal_button.grid(row=10, column=0, sticky="ew", padx=16, pady=(0, 8))

        self.feedback = FeedbackLabel(body)
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
        if hasattr(self, "_rename_scroll"):
            self._rename_scroll._on_content_configure()

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
        from skyadmin_pro.ui.async_ui import run_background

        def work() -> None:
            dest_path: Path | None = None
            try:
                dest_path = file_ops.move_file(selected, self.app.paths.ready_to_upload, new_name)
                client_id = self.app.db.get_or_create_client(client)
                self.app.db.record_document(
                    client_id=client_id,
                    document_type=doc_type,
                    file_name=dest_path.name,
                    file_path=str(dest_path.resolve()),
                    expiry_date=expiry_iso,
                    amount=amount,
                )
                return dest_path
            except OSError as exc:
                raise RuntimeError(f"Could not move the file (in use or permission denied): {exc}") from exc
            except Exception as exc:
                if dest_path is not None:
                    try:
                        file_ops.move_file(dest_path, selected.parent, selected.name)
                    except OSError:
                        pass
                raise RuntimeError(f"Could not record the document: {exc}") from exc

        def on_success(dest_path: Path) -> None:
            self.app.set_status(f"Moved to {FOLDER_READY}: {dest_path.name}")
            self.feedback.success(f"Saved as {dest_path.name}")
            self._last_ready = dest_path
            self.portal_button.configure(state="normal")
            self.refresh()

        def on_error(error: str) -> None:
            self.feedback.error(error)

        def finally_fn() -> None:
            self._busy = False
            self.configure(cursor="")
            self._rename_btn.configure(state="normal")

        run_background(self, work=work, on_success=on_success, on_error=on_error, finally_fn=finally_fn)

    def _open_last_portal(self) -> None:
        if self._last_ready is None:
            self.feedback.error("Rename a file first.")
            return
        launch_portal(self.app, self._last_ready, self.feedback)
