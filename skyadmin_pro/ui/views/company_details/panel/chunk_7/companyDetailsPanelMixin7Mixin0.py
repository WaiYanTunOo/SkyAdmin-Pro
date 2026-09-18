from __future__ import annotations

from skyadmin_pro.services.file_ops import format_thousands
from skyadmin_pro.services.tracking import classify_expiry, days_until, effective_expiry_date


class CompanyDetailsPanelMixin7Mixin0:
    def _refresh_general_subtab(
        self,
        client_id: int | None,
        client: dict | None,
        services: list,
        documents: list,
    ) -> None:
        self.service_tree.apply_theme()
        self.doc_tree.apply_theme()
        if client_id is None:
            self.company_name_label.configure(text="—")
            self.service_tree.set_rows([], empty_message="Select a client to view services.")
            self.doc_tree.set_rows([], empty_message="Select a client to view documents.")
            for var in (
                self.info_reg_number,
                self.info_director,
                self.info_email,
                self.info_contact,
                self.info_capital,
                self.info_vat,
                self.info_address,
            ):
                var.set("")
            self.info_objectives.delete("1.0", "end")
            return
        iids, rows, tags = self._CompanyDetailsPanelMixin7_refresh_gener_p1(client, services)
        self._CompanyDetailsPanelMixin7_refresh_gener_p2(documents, iids, rows, tags)

    def _CompanyDetailsPanelMixin7_refresh_gener_p1(self, client, services):
        self.company_name_label.configure(text=client["name"] if client else "\u2014")
        self.info_reg_number.set((client or {}).get("registration_number") or "")
        self.info_director.set((client or {}).get("director") or "")
        self.info_email.set((client or {}).get("email") or "")
        self.info_contact.set((client or {}).get("contact_number") or "")
        self.info_capital.set((client or {}).get("registered_capital") or "")
        self.info_vat.set((client or {}).get("vat_registration") or "")
        self.info_address.set((client or {}).get("business_address") or "")
        self.info_objectives.delete("1.0", "end")
        self.info_objectives.insert("1.0", (client or {}).get("business_objectives") or "")

        rows, iids, tags = [], [], []
        for item in services:
            progress = item.get("progress") or "Not started"
            row_tags = []
            if progress == "Completed":
                row_tags.append("done")
            elif progress == "Ongoing":
                row_tags.append("wip")
            expiry = item.get("expiry_date")
            eff = effective_expiry_date(expiry, item.get("document_type"))
            left = days_until(eff) if eff else None
            if left is not None:
                tag = classify_expiry(left)
                if tag:
                    row_tags.append(tag)
            rows.append(
                (
                    item.get("document_type") or "\u2014",
                    item.get("start_date") or "\u2014",
                    eff or "\u2014",
                    item.get("payment_date") or "\u2014",
                    format_thousands(item.get("amount")) if item.get("amount") else "\u2014",
                    progress,
                    "Yes" if item.get("paid") else "\u2014",
                )
            )
            iids.append(str(item["id"]))
            tags.append(tuple(row_tags))
        self.service_tree.set_rows(rows, iids=iids, tags=tags, empty_message="No services recorded for this client.")

        rows, iids, tags = [], [], []
        return iids, rows, tags

    def _CompanyDetailsPanelMixin7_refresh_gener_p2(self, documents, iids, rows, tags):
        for item in documents:
            expiry = item.get("expiry_date")
            eff = effective_expiry_date(expiry, item.get("document_type"))
            left = days_until(eff) if eff else None
            row_tags = []
            if left is not None:
                tag = classify_expiry(left)
                if tag:
                    row_tags.append(tag)
            rows.append(
                (
                    item.get("document_type") or "\u2014",
                    item.get("file_name") or "\u2014",
                    eff or "\u2014",
                    (item.get("created_at") or "")[:10],
                )
            )
            iids.append(str(item["id"]))
            tags.append(tuple(row_tags))
        self.doc_tree.set_rows(rows, iids=iids, tags=tags, empty_message="No documents recorded for this client.")
