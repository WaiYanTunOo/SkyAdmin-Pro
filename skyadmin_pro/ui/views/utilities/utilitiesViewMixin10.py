from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.services.translate import DEFAULT_DIRECTION, TRANSLATE_DIRECTIONS
from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.widgets import FeedbackLabel, themed_scrollable_frame


class UtilitiesViewMixin10:
    def _UtilitiesView_build_p1(self):
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_columnconfigure(1, weight=0, minsize=380)
        self.body.grid_rowconfigure(0, weight=1)

        self.hub = themed_scrollable_frame(self.body, corner_radius=12)
        self.hub.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.hub.grid_columnconfigure(0, weight=1)

        self._load_snippets()
        self._build_hub()

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
        translator_sub = ctk.CTkLabel(
            translator,
            text="Sends text over the internet. Not for IRD or portal passwords. Burmese ↔ English; Thai → English.",
            justify="left",
            text_color=TEXT_MUTED,
            anchor="w",
        )
        translator_sub.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        from skyadmin_pro.ui.widgets import bind_wrap_label

        bind_wrap_label(translator_sub, translator, pad=36)

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
        self.translate_btn = ctk.CTkButton(actions, text="Translate", width=120, command=self._translate)
        self.translate_btn.pack(side="left")
        return actions, translator

    def _UtilitiesView_build_p2(self, actions, translator):
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
