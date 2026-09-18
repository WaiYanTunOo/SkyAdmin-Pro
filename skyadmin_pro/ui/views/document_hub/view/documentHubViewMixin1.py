from __future__ import annotations


class DocumentHubViewMixin1:
    def on_show(self) -> None:
        self._polling = True
        # Cancel any previously scheduled poll chain so re-selecting the view
        # cannot stack multiple concurrent polling loops.
        self._cancel_poll()
        current = self._current_tab()
        if current:
            self._ensure_panel(current)
        self.refresh_active_tab(current)
        self._poll()

    def on_hide(self) -> None:
        self._polling = False
        self._cancel_poll()
        try:
            from skyadmin_pro.ui.async_ui import cancel_pump

            cancel_pump(self)
        except Exception:
            pass

    def _cancel_poll(self) -> None:
        if self._poll_after is not None:
            try:
                self.after_cancel(self._poll_after)
            except Exception:
                pass
            self._poll_after = None

    def _active_feedback(self) -> FeedbackLabel | None:
        current = self._current_tab()
        panel = self._lazy_panels.get(current)
        if panel is not None and hasattr(panel, "feedback"):
            return panel.feedback
        return None

    def _poll(self) -> None:
        if not self._polling or not self.winfo_exists():
            return
        try:
            current = self._current_tab()
            if current == "Smart Renamer" and self.renamer is not None:
                self._poll_folder(
                    self.app.paths.staging,
                    known=lambda: self.renamer.file_list._signature,
                    apply=self._apply_renamer_files,
                )
            elif current == "Portal Upload" and self.portal is not None:
                self._poll_folder(
                    self.app.paths.ready_to_upload,
                    known=lambda: self.portal._signature,
                    apply=self._apply_portal_files,
                )
            elif current == "Archive & Clean" and self.archive is not None:
                self._poll_archive_counts()
        except Exception as exc:
            feedback = self._active_feedback()
            if feedback is not None:
                feedback.error(f"Document Hub refresh failed: {exc}")
        if self._polling and self.winfo_exists():
            self._poll_after = self.after(3000, self._poll)

    def _poll_folder(self, folder, *, known, apply) -> None:
        """Scan one folder off the main thread; apply rows on it only."""
        from skyadmin_pro.services import file_ops
        from skyadmin_pro.ui.async_ui import run_background

        try:
            known_sig = known()
        except Exception:
            known_sig = None

        def work():
            return file_ops.list_files_with_signature(folder)

        def on_success(result) -> None:
            if not self._polling or not self.winfo_exists():
                return
            try:
                files, signature = result
            except Exception:
                return
            if signature == known_sig:
                return
            try:
                apply(files, signature)
            except Exception:
                pass

        run_background(self, work=work, on_success=on_success)
