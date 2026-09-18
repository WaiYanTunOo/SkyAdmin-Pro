from __future__ import annotations

from skyadmin_pro.services.translate import direction_codes, translate_text
from skyadmin_pro.services.workflow import copy_to_clipboard


class UtilitiesViewMixin9:
    def _finish_copy(self, label: str, text: str, close=None) -> None:
        try:
            copy_to_clipboard(text, tk_window=self.app)
        except Exception as exc:
            self.hub_feedback.error(str(exc))
            if close is not None:
                try:
                    close.destroy()
                except Exception:
                    pass
            return
        if close is not None:
            try:
                close.destroy()
            except Exception:
                pass
        self.hub_feedback.success(f"Copied: {label}")
        self.app.set_status(f"Copied “{label}” to the clipboard.")

    def _set_output(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        if text:
            self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def _translate(self) -> None:
        if self._busy:
            return
        source_text = self.source.get("1.0", "end").strip()
        if not source_text:
            self.translator_feedback.error("Paste text first.")
            return
        source, target = direction_codes(self.direction.get())
        self._busy = True
        self.translate_btn.configure(state="disabled", text="Translating…")
        self.translator_feedback.info("Translating…")
        from skyadmin_pro.ui.async_ui import run_background

        def work() -> str:
            source, target = direction_codes(self.direction.get())
            return translate_text(source_text, source, target)

        def _translate_reset(self) -> None:
            self._busy = False
            self.translate_btn.configure(state="normal", text="Translate")

        run_background(
            self,
            work=work,
            on_success=self._translate_ok,
            on_error=self._translate_failed,
            finally_fn=self._translate_reset,
            feedback=self.translator_feedback,
        )

    def _translate_ok(self, result: str) -> None:
        self._set_output(result)
        try:
            copy_to_clipboard(result, tk_window=self.app)
            self.translator_feedback.success("Translated. Result is also on the clipboard.")
        except Exception:
            self.translator_feedback.success("Translated.")
        self.app.set_status("Translation ready.")

    def _translate_failed(self, message: str) -> None:
        self.translator_feedback.error(message)

    def _copy_output(self) -> None:
        text = self.output.get("1.0", "end").strip()
        if not text:
            self.translator_feedback.error("Nothing to copy yet.")
            return
        try:
            copy_to_clipboard(text, tk_window=self.app)
        except Exception as exc:
            self.translator_feedback.error(str(exc))
            return
        self.translator_feedback.success("Copied to the clipboard.")

    def _clear_translator(self) -> None:
        self.source.delete("1.0", "end")
        self._set_output("")
        self.translator_feedback.clear()
