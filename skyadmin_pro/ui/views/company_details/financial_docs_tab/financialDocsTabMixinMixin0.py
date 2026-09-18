from __future__ import annotations

from pathlib import Path

import customtkinter as ctk


class FinancialDocsTabMixinMixin0:
    def _build_financial_docs(self, master) -> ctk.CTkFrame:
        frame = self._FinancialDocsTabMixin_build_financial_d_p1(master)
        self._FinancialDocsTabMixin_build_financial_d_p2(frame)

        return frame

    def _refresh_financial_docs(self) -> None:
        client_id = self._selected_client_id()
        self.fin_doc_tree.apply_theme()
        if client_id is None:
            self.fin_doc_tree.set_rows([], empty_message="Select a client to view financial documents.")
            self.fin_summary_label.configure(text="")
            return
        cat_filter = self.fin_category_filter.get()
        category = None if cat_filter == "All" else cat_filter
        docs = self.app.db.list_financial_documents(client_id, category)
        summary = self.app.db.financial_doc_summary(client_id)
        total = sum(summary.values())
        parts = [f"{cat}: {n}" for cat, n in sorted(summary.items())]
        self.fin_summary_label.configure(text=f"{total} document(s)" + (f" — {', '.join(parts)}" if parts else ""))
        rows, iids = [], []
        for d in docs:
            rows.append(
                (
                    d.get("doc_date") or "—",
                    d.get("category") or "—",
                    d.get("subcategory") or "—",
                    d.get("file_name") or "—",
                    d.get("amount") or "—",
                    d.get("description") or "—",
                )
            )
            iids.append(str(d["id"]))
        self.fin_doc_tree.set_rows(rows, iids=iids, empty_message="No financial documents for this client yet.")

    def _on_financial_doc_drop(self, paths: list[Path]) -> None:
        if not paths:
            return
        self._add_financial_doc(str(paths[0]))
