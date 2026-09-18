from __future__ import annotations

from datetime import date

from skyadmin_pro.config import DOC_TYPE_INVOICE, DOC_TYPES_WITH_AMOUNT, DOC_TYPES_WITH_EXPIRY
from skyadmin_pro.services import file_ops
from skyadmin_pro.ui.views.document_hub.helpers import launch_portal


class SmartRenamerPanelMixin1:
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
        self._SmartRenamerPanel_rename_and_move_p1(amount, client, doc_type, expiry_iso, new_name, selected)

    def _open_last_portal(self) -> None:
        if self._last_ready is None:
            self.feedback.error("Rename a file first.")
            return
        launch_portal(self.app, self._last_ready, self.feedback)
