from __future__ import annotations

from tkinter import messagebox


class BackupMixinMixin10:
    def _normalize_portable_paths(self) -> None:
        from skyadmin_pro.services.portable_paths import normalize_portable_paths

        if not messagebox.askyesno(
            "Make paths portable",
            "Rewrite document file paths to workspace-relative form "
            "(works on any PC and maps to Google Drive).\n\n"
            "Unresolvable broken links are cleared; service rows are kept.\n"
            "PDFs on disk are not deleted.\n\nContinue?",
            parent=self.winfo_toplevel(),
        ):
            return
        root = getattr(getattr(self.app, "paths", None), "root", None)
        result = normalize_portable_paths(self.app.db, local_root=root)
        self.feedback.success(
            f"Portable paths: linked {result['linked']}, "
            f"already OK {result['already_relative']}, "
            f"cleared {result['cleared']}."
        )
