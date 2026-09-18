from __future__ import annotations

from datetime import date
from pathlib import Path

from skyadmin_pro.config import FOLDER_READY
from skyadmin_pro.services import file_ops


class AgentBundlePanelMixin1:
    def _merge(self) -> None:
        if self._busy:
            return
        sources = list(self.path_list.paths)
        if not sources:
            self.feedback.error("Add at least one PDF file to merge.")
            return
        name = self.output_var.get().strip() or f"{date.today().strftime('%Y%m%d')}_AgentBundle.pdf"
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        dest_dir = self.app.paths.ready_to_upload if self.dest_menu.get() == FOLDER_READY else self.app.paths.staging
        target = dest_dir / name
        self._busy = True
        self._merge_btn.configure(state="disabled")
        self.configure(cursor="watch")
        self.feedback.info(f"Merging {len(sources)} PDF(s)… please wait.")
        self.update_idletasks()
        from skyadmin_pro.ui.async_ui import run_background

        def work() -> Path:
            return file_ops.merge_pdfs(sources, target)

        def on_success(output: Path) -> None:
            self.feedback.success(f"Bundle saved as {output.name}")
            self.app.set_status(f"Merged {len(sources)} PDFs → {output.name}")

        def finally_fn() -> None:
            self._busy = False
            self.configure(cursor="")
            self._merge_btn.configure(state="normal")

        run_background(
            self,
            work=work,
            on_success=on_success,
            on_error=lambda err: self.feedback.error(f"Merge failed: {err}"),
            finally_fn=finally_fn,
        )
