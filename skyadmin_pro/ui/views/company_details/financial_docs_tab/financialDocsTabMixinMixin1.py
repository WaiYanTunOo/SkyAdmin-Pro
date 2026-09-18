from __future__ import annotations

import os
from pathlib import Path

import customtkinter as ctk

from skyadmin_pro.config import FINANCIAL_DOC_CATEGORIES, FINANCIAL_DOC_FOLDER_MAP
from skyadmin_pro.services.file_ops import open_in_file_manager
from skyadmin_pro.services.workflow import resolve_client_folder


class FinancialDocsTabMixinMixin1:
    def _add_financial_doc(self, preset_path: str = "") -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        file_path = self._FinancialDocsTabMixin_add_financial_doc_p1(preset_path)
        if not file_path:
            return
        amt_var, cat_var, date_var, desc_var, dialog, file_name, sub_var = (
            self._FinancialDocsTabMixin_add_financial_doc_p2(file_path, FINANCIAL_DOC_CATEGORIES)
        )

        def _confirm() -> None:
            category = cat_var.get()
            subcategory = sub_var.get()
            # Copy file to workspace
            client = self.app.db.get_client(client_id)
            client_name = (client or {}).get("name") or "client"
            folder_name = FINANCIAL_DOC_FOLDER_MAP.get(category, "General_Expenses")
            try:
                client_folder = resolve_client_folder(self.app.paths.clients, client_name, create=True)
            except Exception as exc:
                self.feedback.error(str(exc))
                return
            dest_dir = client_folder / "04_Financial_Docs" / folder_name
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                self.feedback.error(f"Cannot create document folder: {exc}")
                return
            dest_path = dest_dir / file_name
            # Prevent duplicate file copies — add numeric suffix if exists
            if dest_path.exists():
                stem = dest_path.stem
                suffix = dest_path.suffix
                counter = 1
                while dest_path.exists():
                    dest_path = dest_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            try:
                import shutil

                shutil.copy2(file_path, dest_path)
                stored = str(dest_path)
            except Exception:
                stored = ""
            self.app.db.add_financial_document(
                client_id=client_id,
                category=category,
                subcategory=subcategory,
                file_name=dest_path.name,
                file_path=file_path,
                stored_path=stored,
                amount=amt_var.get().strip(),
                doc_date=date_var.get().strip(),
                description=desc_var.get().strip(),
            )
            dialog.destroy()
            self.feedback.success(f"Document '{dest_path.name}' added.")
            self._refresh_financial_docs()

        ctk.CTkButton(
            dialog,
            text="Add",
            width=100,
            command=_confirm,
        ).grid(row=5, column=0, columnspan=2, pady=(12, 16))

    def _open_financial_doc(self) -> None:
        selected = self.fin_doc_tree.tree.selection()
        if not selected:
            self.feedback.error("Select a document first.")
            return
        doc_id = int(selected[0])
        doc = self.app.db.get_financial_document(doc_id)
        if not doc:
            return
        path = doc.get("stored_path") or doc.get("file_path") or ""
        if not path or not os.path.exists(path):
            self.feedback.error("File not found on disk.")
            return
        try:
            open_in_file_manager(Path(path))
        except (OSError, RuntimeError) as exc:
            self.feedback.error(f"Could not open file: {exc}")
