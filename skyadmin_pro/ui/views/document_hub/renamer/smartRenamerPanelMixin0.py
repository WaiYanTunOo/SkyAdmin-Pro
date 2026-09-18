from __future__ import annotations

from datetime import date

from skyadmin_pro.config import DOC_TYPE_INVOICE, DOC_TYPES_WITH_AMOUNT, DOC_TYPES_WITH_EXPIRY
from skyadmin_pro.services import file_ops


class SmartRenamerPanelMixin0:
    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color="transparent")
        body, right = self._SmartRenamerPanel__init__p1(app)
        self._SmartRenamerPanel__init__p2(body)
        self._SmartRenamerPanel__init__p3(body, right)

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
