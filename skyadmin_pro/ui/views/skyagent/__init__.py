"""SkyAgent chat panel — AI co-pilot for account administrators."""

from __future__ import annotations

import customtkinter as ctk

from .bubbles import ChatBubble
from .chat_mixin import SkyAgentChatMixin


class SkyAgentChat(SkyAgentChatMixin, ctk.CTkToplevel):
    pass
