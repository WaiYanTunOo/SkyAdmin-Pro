from __future__ import annotations


class DocumentHubViewMixin2:
    def _poll_archive_counts(self) -> None:
        """Scan both archive folders off the main thread."""
        from skyadmin_pro.services import file_ops
        from skyadmin_pro.ui.async_ui import run_background

        panel = self.archive
        try:
            known_sig = panel._archive_signature
        except Exception:
            known_sig = None
        ready_folder = self.app.paths.ready_to_upload
        staging_folder = self.app.paths.staging

        def work():
            ready, ready_sig = file_ops.list_files_with_signature(ready_folder)
            staging, staging_sig = file_ops.list_files_with_signature(staging_folder)
            return ready, ready_sig, staging, staging_sig

        def on_success(result) -> None:
            if not self._polling or not self.winfo_exists():
                return
            try:
                ready, ready_sig, staging, staging_sig = result
            except Exception:
                return
            if (ready_sig, staging_sig) == known_sig:
                return
            try:
                panel.render_counts(ready, ready_sig, staging, staging_sig)
            except Exception as e:
                import logging

                logging.error(f"UI Error: {e}")

        run_background(self, work=work, on_success=on_success)

    def _apply_renamer_files(self, files, signature) -> None:
        panel = self.renamer
        if panel is None:
            return
        panel.file_list.set_files(files, signature=signature)
        panel._update_preview()

    def _apply_portal_files(self, files, signature) -> None:
        panel = self.portal
        if panel is None:
            return
        panel.render_files(files, signature)

    def mark_stale(self) -> None:
        """Force next refresh to reload even if signature unchanged."""
        for panel in self._lazy_panels.values():
            if hasattr(panel, "_signature"):
                try:
                    panel._signature = None  # type: ignore[attr-defined]
                except Exception as e:
                    import logging

                    logging.error(f"UI Error: {e}")
