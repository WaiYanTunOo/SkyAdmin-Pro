"""Utilities: Burmese replies for clients, English + krub for suppliers, plus translation."""

from __future__ import annotations

import threading

import customtkinter as ctk

from skyadmin_pro.services.snippets import CHECKLISTS, CLIENT_REPLIES, SUPPLIER_REPLIES, Snippet
from skyadmin_pro.services.translate import (
    DEFAULT_DIRECTION,
    TRANSLATE_DIRECTIONS,
    direction_codes,
    translate_text,
)
from skyadmin_pro.services.workflow import copy_to_clipboard
from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.widgets import FeedbackLabel


class UtilitiesView(BaseView):
    title = "Utilities"
    subtitle = "Burmese to clients · English + krub / 🙏 to suppliers · translator."

    def build(self) -> None:
        self.body.grid_columnconfigure(0, weight=3)
        self.body.grid_columnconfigure(1, weight=2)
        self.body.grid_rowconfigure(0, weight=1)

        hub = ctk.CTkScrollableFrame(self.body, corner_radius=12)
        hub.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        hub.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hub,
            text="To Burmese clients (Burmese)",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))
        ctk.CTkLabel(
            hub,
            text="Messages in Burmese. Click to copy.",
            text_color=("gray40", "gray70"),
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))
        self._snippet_grid(hub, CLIENT_REPLIES, start_row=2, columns=3)

        ctk.CTkLabel(
            hub,
            text="To Thai suppliers (English + krub)",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=3, column=0, sticky="w", padx=12, pady=(18, 4))
        ctk.CTkLabel(
            hub,
            text="Simple English, krub, 🙏. No Thai script. Click to copy.",
            text_color=("gray40", "gray70"),
            anchor="w",
        ).grid(row=4, column=0, sticky="w", padx=12, pady=(0, 8))
        self._snippet_grid(hub, SUPPLIER_REPLIES, start_row=5, columns=3)

        ctk.CTkLabel(
            hub,
            text="Checklists",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=6, column=0, sticky="w", padx=12, pady=(18, 4))
        ctk.CTkLabel(
            hub,
            text="Visa, company, work permit, accounting, and courier — Myanmar clients in Thailand.",
            text_color=("gray40", "gray70"),
            anchor="w",
        ).grid(row=7, column=0, sticky="w", padx=12, pady=(0, 8))
        self._snippet_grid(hub, CHECKLISTS, start_row=8, columns=2)

        self.hub_feedback = FeedbackLabel(hub)
        self.hub_feedback.grid(row=9, column=0, sticky="ew", padx=12, pady=(8, 16))

        translator = ctk.CTkFrame(self.body, corner_radius=12)
        translator.grid(row=0, column=1, sticky="nsew")
        translator.grid_columnconfigure(0, weight=1)
        translator.grid_rowconfigure(3, weight=1)
        translator.grid_rowconfigure(6, weight=1)

        ctk.CTkLabel(
            translator,
            text="Translator",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 4))
        ctk.CTkLabel(
            translator,
            text="Burmese ↔ English for clients. Thai → English to read supplier papers. Needs internet.",
            wraplength=360,
            justify="left",
            text_color=("gray40", "gray70"),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

        self.direction = ctk.CTkOptionMenu(
            translator,
            values=[item[0] for item in TRANSLATE_DIRECTIONS],
            command=self._on_direction,
        )
        self.direction.set(DEFAULT_DIRECTION)
        self.direction.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 8))

        self.source = ctk.CTkTextbox(translator, wrap="word")
        self.source.grid(row=3, column=0, sticky="nsew", padx=16)

        actions = ctk.CTkFrame(translator, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="ew", padx=16, pady=10)
        self.translate_btn = ctk.CTkButton(
            actions, text="Translate", width=120, command=self._translate
        )
        self.translate_btn.pack(side="left")
        self.copy_btn = ctk.CTkButton(
            actions,
            text="Copy result",
            width=120,
            fg_color="transparent",
            border_width=1,
            command=self._copy_output,
        )
        self.copy_btn.pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            actions,
            text="Clear",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=self._clear_translator,
        ).pack(side="left", padx=(8, 0))

        self.output_label = ctk.CTkLabel(translator, text="English", anchor="w")
        self.output_label.grid(row=5, column=0, sticky="w", padx=16)
        self.output = ctk.CTkTextbox(translator, wrap="word", state="disabled")
        self.output.grid(row=6, column=0, sticky="nsew", padx=16, pady=(4, 8))

        self.translator_feedback = FeedbackLabel(translator)
        self.translator_feedback.grid(row=7, column=0, sticky="ew", padx=16, pady=(0, 16))

        self._busy = False
        self._on_direction(DEFAULT_DIRECTION)

    def _on_direction(self, choice: str) -> None:
        _source, target = direction_codes(choice)
        names = {"en": "English", "my": "Burmese", "th": "Thai"}
        self.output_label.configure(text=names.get(target, target))

    def _snippet_grid(
        self,
        master: ctk.CTkScrollableFrame,
        snippets: tuple[Snippet, ...],
        *,
        start_row: int,
        columns: int,
    ) -> None:
        grid = ctk.CTkFrame(master, fg_color="transparent")
        grid.grid(row=start_row, column=0, sticky="ew", padx=12)
        for col in range(columns):
            grid.grid_columnconfigure(col, weight=1, uniform="snip")
        for index, snippet in enumerate(snippets):
            row, column = divmod(index, columns)
            ctk.CTkButton(
                grid,
                text=snippet.label,
                height=40,
                command=lambda item=snippet: self._copy_snippet(item),
            ).grid(row=row, column=column, sticky="ew", padx=4, pady=4)

    def _copy_snippet(self, snippet: Snippet) -> None:
        try:
            copy_to_clipboard(snippet.text, tk_window=self.app)
        except Exception as exc:
            self.hub_feedback.error(str(exc))
            return
        self.hub_feedback.success(f"Copied: {snippet.label}")
        self.app.set_status(f"Copied “{snippet.label}” to the clipboard.")

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

        def worker() -> None:
            error: str | None = None
            result = ""
            try:
                result = translate_text(source_text, source, target)
            except Exception as exc:
                error = str(exc)

            def done() -> None:
                if not self.winfo_exists():
                    return
                if error:
                    self._translate_failed(error)
                else:
                    self._translate_ok(result)

            try:
                self.after(0, done)
            except Exception:
                return

        threading.Thread(target=worker, daemon=True).start()

    def _translate_ok(self, result: str) -> None:
        self._busy = False
        self.translate_btn.configure(state="normal", text="Translate")
        self._set_output(result)
        try:
            copy_to_clipboard(result, tk_window=self.app)
            self.translator_feedback.success("Translated. Result is also on the clipboard.")
        except Exception:
            self.translator_feedback.success("Translated.")
        self.app.set_status("Translation ready.")

    def _translate_failed(self, message: str) -> None:
        self._busy = False
        self.translate_btn.configure(state="normal", text="Translate")
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
