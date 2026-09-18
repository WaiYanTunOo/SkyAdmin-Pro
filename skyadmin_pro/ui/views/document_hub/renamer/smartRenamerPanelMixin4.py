from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from skyadmin_pro.config import FOLDER_READY
from skyadmin_pro.services import file_ops
from skyadmin_pro.ui.theme import WRAP_CARD
from skyadmin_pro.ui.widgets import FeedbackLabel


class SmartRenamerPanelMixin4:
    def _SmartRenamerPanel__init__p3(self, body, right):
        ctk.CTkLabel(body, text="New filename", anchor="w").grid(row=7, column=0, sticky="w", padx=16, pady=(16, 4))
        self.preview = ctk.CTkLabel(
            body,
            text="Select a file to preview the name.",
            anchor="w",
            wraplength=WRAP_CARD,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.preview.grid(row=8, column=0, sticky="ew", padx=16)
        # Keep preview readable on narrow windows — update wrap with card width.
        right.bind("<Configure>", lambda e: self.preview.configure(wraplength=max(220, e.width - 32)))

        self._busy = False
        self._rename_btn = ctk.CTkButton(
            body,
            text=f"Rename & move to {FOLDER_READY}",
            height=40,
            command=self._rename_and_move,
        )
        self._rename_btn.grid(row=9, column=0, sticky="ew", padx=16, pady=(18, 6))

        self.portal_button = ctk.CTkButton(
            body,
            text="Open portal & copy path",
            height=36,
            fg_color="transparent",
            border_width=1,
            state="disabled",
            command=self._open_last_portal,
        )
        self.portal_button.grid(row=10, column=0, sticky="ew", padx=16, pady=(0, 8))

        self.feedback = FeedbackLabel(body)
        self.feedback.grid(row=11, column=0, sticky="ew", padx=16, pady=(0, 16))

        self._last_ready: Path | None = None
        self._on_type_change(self.type_menu.get())

    def _SmartRenamerPanel_rename_and_move_p1(self, amount, client, doc_type, expiry_iso, new_name, selected):
        self._busy = True
        self._rename_btn.configure(state="disabled")
        self.configure(cursor="watch")
        self.feedback.info("Moving file… please wait.")
        self.update_idletasks()
        from skyadmin_pro.ui.async_ui import run_background

        def work() -> None:
            dest_path: Path | None = None
            try:
                dest_path = file_ops.move_file(selected, self.app.paths.ready_to_upload, new_name)
                client_id = self.app.db.get_or_create_client(client)
                self.app.db.record_document(
                    client_id=client_id,
                    document_type=doc_type,
                    file_name=dest_path.name,
                    file_path=str(dest_path.resolve()),
                    expiry_date=expiry_iso,
                    amount=amount,
                )
                return dest_path
            except OSError as exc:
                raise RuntimeError(f"Could not move the file (in use or permission denied): {exc}") from exc
            except Exception as exc:
                if dest_path is not None:
                    try:
                        file_ops.move_file(dest_path, selected.parent, selected.name)
                    except OSError:
                        pass
                raise RuntimeError(f"Could not record the document: {exc}") from exc

        def on_success(dest_path: Path) -> None:
            self.app.set_status(f"Moved to {FOLDER_READY}: {dest_path.name}")
            self.feedback.success(f"Saved as {dest_path.name}")
            self._last_ready = dest_path
            self.portal_button.configure(state="normal")
            self.refresh()

        def on_error(error: str) -> None:
            self.feedback.error(error)

        def finally_fn() -> None:
            self._busy = False
            self.configure(cursor="")
            self._rename_btn.configure(state="normal")

        run_background(self, work=work, on_success=on_success, on_error=on_error, finally_fn=finally_fn)
