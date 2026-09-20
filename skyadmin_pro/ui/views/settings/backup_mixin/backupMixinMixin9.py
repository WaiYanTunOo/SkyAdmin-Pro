from __future__ import annotations

from tkinter import messagebox


class BackupMixinMixin9:
    def _clear_broken_document_files(self) -> None:
        from skyadmin_pro.services.drive.clear_attachments import clear_document_file_attachments

        if not messagebox.askyesno(
            "Clear document file links",
            "Clear broken file name/path links on documents so you can re-attach cleanly?\n\n"
            "• Keeps service rows (VO, CSH, accounting, etc.)\n"
            "• Clears file_name, file_path, drive_file_id when the file is missing\n"
            "• Does NOT delete PDFs on disk\n"
            "• Rows with a unique matching PDF under Clients are kept\n\n"
            "Continue?",
            parent=self.winfo_toplevel(),
        ):
            return
        root = getattr(getattr(self.app, "paths", None), "root", None)
        result = clear_document_file_attachments(self.app.db, local_root=root, only_broken=True)
        self.feedback.success(
            f"Cleared {result['cleared']} broken file link(s); kept {result['kept']} with files on disk."
        )
