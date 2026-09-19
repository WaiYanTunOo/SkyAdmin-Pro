from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED


class LicenseMixinMixin5:
    def _on_sync_auto_interval(self) -> None:
        from skyadmin_pro.config import SETTING_SYNC_AUTO_INTERVAL
        from skyadmin_pro.services.data_sync import normalize_sync_auto_interval

        value = normalize_sync_auto_interval(self._sync_auto_interval_var.get())
        self._sync_auto_interval_var.set(value)
        self.app.db.set_setting(SETTING_SYNC_AUTO_INTERVAL, value)
        self._nudge_auto_sync()
        self.app.set_status(f"Auto sync interval: {value}")

    def _nudge_auto_sync(self) -> None:
        scheduler = getattr(self.app, "_auto_sync", None)
        nudge = getattr(scheduler, "nudge", None)
        if callable(nudge):
            try:
                nudge()
            except Exception:
                pass

    def _sync_now(self) -> None:
        from skyadmin_pro.services.data_sync import sync_data
        from skyadmin_pro.services.license import fetch_revocations
        from skyadmin_pro.ui.async_ui import run_background

        self._begin_license_background("sync", "Syncing license + data…")
        self.daily_sync_label.configure(text="Syncing…", text_color=TEXT_MUTED)
        self.data_sync_label.configure(text="")

        def work() -> tuple[bool, str]:
            lic_ok, lic_msg = fetch_revocations(timeout=6)
            data_ok, data_msg = sync_data(self.app.db, timeout=25)
            ok = lic_ok and data_ok
            if lic_ok and data_ok:
                msg = f"{lic_msg.splitlines()[0]} · {data_msg}"
            elif not lic_ok:
                msg = lic_msg
            else:
                msg = data_msg
            return ok, msg

        def on_success(result: tuple[bool, str]) -> None:
            ok, msg = result
            if ok:
                self.feedback.success(msg.splitlines()[0])
            else:
                self.feedback.error(msg.splitlines()[0])
            self._refresh_license_label()
            self._refresh_update_banner()
            try:
                self.app.refresh_sidebar_status()
                self.app.set_status(msg.splitlines()[0])
            except Exception:
                pass

        run_background(
            self,
            work=work,
            on_success=on_success,
            on_error=lambda err: self.feedback.error(err.splitlines()[0]),
            finally_fn=self._end_license_background,
            feedback=self.feedback,
        )

    def _show_license(self) -> None:
        from skyadmin_pro.config import LEGAL_LICENSE_TEXT

        self._show_legal("License Agreement", LEGAL_LICENSE_TEXT)

    def _show_disclaimer(self) -> None:
        from skyadmin_pro.config import LEGAL_DISCLAIMER_TEXT

        self._show_legal("Disclaimer", LEGAL_DISCLAIMER_TEXT)

    def _show_legal(self, title: str, text: str) -> None:
        top = ctk.CTkToplevel(self)
        top.title(f"SkyAdmin Pro — {title}")
        top.geometry("720x560")
        top.transient(self.winfo_toplevel())
        from skyadmin_pro.ui.widgets import make_modal

        make_modal(top)
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(0, weight=1)
        box = ctk.CTkTextbox(top, wrap="word")
        box.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        box.insert("1.0", text)
        box.configure(state="disabled")
        ctk.CTkButton(top, text="Close", width=110, command=top.destroy).grid(row=1, column=0, pady=(0, 16))
