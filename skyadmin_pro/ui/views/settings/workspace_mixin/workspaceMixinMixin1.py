from __future__ import annotations

from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from skyadmin_pro.config import SETTING_APPEARANCE_MODE, SETTING_COLOR_THEME
from skyadmin_pro.services.file_ops import open_in_file_manager


class WorkspaceMixinMixin1:
    def _open_suppliers(self) -> None:
        self._open_path(self.app.paths.suppliers)

    def _open_path(self, path: Path) -> None:
        try:
            open_in_file_manager(path)
        except Exception as exc:
            self.feedback.error(str(exc))

    def _on_appearance_change(self, choice: str) -> None:
        mode = choice.lower()
        ctk.set_appearance_mode(mode)
        self.app.db.set_setting(SETTING_APPEARANCE_MODE, mode)
        self.app.apply_app_theme()

    def _on_color_theme_change(self, choice: str) -> None:
        ctk.set_default_color_theme(choice)
        self.app.db.set_setting(SETTING_COLOR_THEME, choice)
        self.feedback.info(f"Accent set to {choice}. Restart the app to fully apply button colors.")

    def _load_directory_lists(self) -> None:
        self.departments_text.delete("1.0", "end")
        self.departments_text.insert("1.0", "\n".join(self.app.db.list_departments()))

    def _save_directory_lists(self) -> None:
        depts = [line.strip() for line in self.departments_text.get("1.0", "end").splitlines() if line.strip()]
        try:
            self.app.db.set_departments(depts)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success("Department list saved.")
        self._load_directory_lists()

    def _import_directory_lists(self) -> None:
        new_clients, new_depts = self.app.db.import_directory_from_data()
        self._load_directory_lists()
        self.feedback.success(
            f"Imported {new_clients} client company name(s) and {new_depts} department(s) from existing data."
        )

    def _import_clients_csv(self) -> None:
        from skyadmin_pro.services.importer import import_clients_from_csv

        csv_path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Import clients from CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not csv_path:
            return
        try:
            stats = import_clients_from_csv(self.app.db, Path(csv_path))
        except Exception as exc:
            self.feedback.error(f"Import failed: {exc}")
            return
        parts = []
        if stats["imported"]:
            parts.append(f"{stats['imported']} imported")
        if stats["skipped"]:
            parts.append(f"{stats['skipped']} skipped (duplicate)")
        if stats["errors"]:
            parts.append(f"{stats['errors']} errors")
        self.feedback.success("Import complete: " + ", ".join(parts) if parts else "No rows processed.")
        self._load_directory_lists()

    def _on_language_change(self, lang: str) -> None:
        from skyadmin_pro.services import i18n

        i18n.set_language(lang.lower())
        self.app.db.set_setting("ui_language", lang.lower())
        self.feedback.info(f"Language set to {lang}. Restart the app to fully apply.")

    def _save_tagline(self) -> None:
        from skyadmin_pro.config import APP_TAGLINE, SETTING_APP_TAGLINE

        text = self.tagline_var.get().strip()
        saved = text or APP_TAGLINE
        self.app.db.set_setting(SETTING_APP_TAGLINE, saved)
        self.feedback.success("Tagline saved.")
        self.app.refresh_tagline(saved)
        self.app.set_status(f"Tagline: {saved}")
