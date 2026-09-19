"""VO/CSH Setup rollout — Finance sidebar page (not Company Details)."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.widgets import FeedbackLabel

from .mixin0 import VoCshSetupPanelMixin0
from .mixin1 import VoCshSetupPanelMixin1


class VoCshSetupPanel(VoCshSetupPanelMixin0, VoCshSetupPanelMixin1, ctk.CTkFrame):
    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        frame = self._build_vo_csh_setup(self)
        frame.grid(row=0, column=0, sticky="nsew")
