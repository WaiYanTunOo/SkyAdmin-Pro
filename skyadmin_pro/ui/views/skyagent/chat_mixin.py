"""SkyAgent chat panel — data-first co-pilot for account administrators."""

from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from typing import Any

from skyadmin_pro.ui.async_ui import cancel_pump, run_background

from ._chat_build import build_header, build_history, build_input
from ._msg_helpers import _winfo_ok, add_bubble, safe_error_text, trim_messages

logger = logging.getLogger(__name__)


class SkyAgentChatMixin:
    """Floating chat panel with message history and input."""

    _MAX_MESSAGES = 100

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.app = app
        self.title("SkyAgent")
        self.geometry("480x600")
        self.resizable(True, True)
        self.transient(app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._status = build_header(self)
        self._history = build_history(self)
        self._input_var = tk.StringVar()
        build_input(self, self._input_var, self._send)
        self.bind("<Escape>", self._on_escape)
        self._llm = self._init_llm()
        self._rag: Any = None
        self._messages: list[dict[str, str]] = []
        self._send_seq = 0
        self._busy = False
        self._status.configure(text=self._ready_label())

    def _init_llm(self) -> Any:
        from skyadmin_pro.services.skyagent._https_llm import try_https_llm_from_env
        from skyadmin_pro.services.skyagent.llm_interface import SkyAgentLLM

        provider = try_https_llm_from_env()
        return SkyAgentLLM(provider) if provider is not None else None

    def _get_rag(self) -> Any:
        if self._rag is None:
            from skyadmin_pro.services.skyagent import index_docs_folder

            root = Path(__file__).resolve().parents[4]
            self._rag = index_docs_folder(root / "docs")
        return self._rag

    def _ready_label(self) -> str:
        if self._llm is not None:
            return "Ready (online configured)"
        return "Ready (offline)"

    def _send(self) -> None:
        if self._busy:
            return
        text = self._input_var.get().strip()
        if not text:
            return
        self._input_var.set("")
        add_bubble(self._history, text, is_user=True)
        self._messages.append({"role": "user", "content": text})
        self._send_seq += 1
        seq = self._send_seq
        self._busy = True
        self._status.configure(text="Thinking\u2026")

        def work() -> str:
            from skyadmin_pro.services.skyagent._router import answer
            from skyadmin_pro.services.skyagent.readonly import SkyAgentDB

            return answer(text, SkyAgentDB(self.app.db), self._get_rag(), llm=self._llm)

        def on_success(response: str) -> None:
            self._busy = False
            if seq != self._send_seq or not _winfo_ok(self):
                return
            add_bubble(self._history, response, is_user=False)
            self._messages.append({"role": "agent", "content": response})
            trim_messages(self._messages, self._history, self._MAX_MESSAGES)
            self._status.configure(text=self._ready_label())

        def on_error(err: str) -> None:
            self._busy = False
            if seq != self._send_seq or not _winfo_ok(self):
                return
            add_bubble(self._history, safe_error_text(err), is_user=False)
            self._status.configure(text=self._ready_label())

        run_background(self, work=work, on_success=on_success, on_error=on_error)

    def _on_escape(self, _event=None):
        """Close chat on Escape unless a DatePicker calendar is open."""
        from skyadmin_pro.ui.widgets import DatePickerField

        if any(
            DatePickerField._widget_alive(getattr(field, "_calendar_top", None))
            for field in list(DatePickerField._open_fields)
        ):
            return "break"
        self.destroy()

    def destroy(self) -> None:
        try:
            cancel_pump(self)
        except Exception:
            logger.debug("Failed to cancel async pump")
        self._llm = None
        self._rag = None
        super().destroy()
