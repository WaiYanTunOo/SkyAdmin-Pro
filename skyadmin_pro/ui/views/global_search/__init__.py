"""Global search dialog — searches across clients, tasks, documents, and contacts."""

from __future__ import annotations

import customtkinter as ctk

from .globalSearchDialogMixin0 import GlobalSearchDialogMixin0
from .globalSearchDialogMixin1 import GlobalSearchDialogMixin1
from .globalSearchDialogMixin2 import GlobalSearchDialogMixin2
from .globalSearchDialogMixin3 import GlobalSearchDialogMixin3


class GlobalSearchDialog(
    GlobalSearchDialogMixin0,
    GlobalSearchDialogMixin1,
    GlobalSearchDialogMixin2,
    GlobalSearchDialogMixin3,
    ctk.CTkToplevel,
):
    pass
