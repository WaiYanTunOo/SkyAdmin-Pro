"""Document Hub — Archive & Clean panel."""

from __future__ import annotations

import customtkinter as ctk

from .archivePanelMixin0 import ArchivePanelMixin0
from .archivePanelMixin1 import ArchivePanelMixin1


class ArchivePanel(ArchivePanelMixin0, ArchivePanelMixin1, ctk.CTkFrame):
    pass
