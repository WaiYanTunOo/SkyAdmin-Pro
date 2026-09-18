from __future__ import annotations

from tkinter import messagebox

from skyadmin_pro.services import file_ops


class ArchivePanelMixin1:
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
        from skyadmin_pro.ui.async_ui import run_background

        def work() -> ArchiveResult:
            return file_ops.archive_ready_and_clean_staging(self.app.paths)

        def on_success(result) -> None:
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

        def finally_fn() -> None:
            self._busy = False
            self.configure(cursor="")
            self._archive_btn.configure(state="normal")

        run_background(
            self,
            work=work,
            on_success=on_success,
            on_error=lambda err: self.feedback.error(f"Archive failed: {err}"),
            finally_fn=finally_fn,
        )
