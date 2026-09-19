from __future__ import annotations

from pathlib import Path

from skyadmin_pro.config import MOBILE_VIEWER_URL, OWNER_EMAIL


class LicenseMixinMixin0:
    def _refresh_update_banner(self) -> None:
        from skyadmin_pro.config import APP_VERSION
        from skyadmin_pro.services.license import (
            is_newer_version,
            read_update_info,
        )

        info = read_update_info()
        if info and is_newer_version(info["version"], APP_VERSION):
            self.update_label.configure(
                text=(
                    f"⬆ Update available: v{info['version']} (you have v{APP_VERSION}). "
                    "Download the new build, then replace your old exe."
                )
            )
            self._update_url = info.get("url") or ""
            self._update_download_btn.configure(
                text="Download update" if self._update_url else "No download URL",
                state="normal" if self._update_url else "disabled",
            )
            self.update_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        else:
            self.update_frame.grid_forget()

    def _open_update_url(self) -> None:
        import webbrowser

        url = getattr(self, "_update_url", "")
        if url:
            webbrowser.open(url)

    def _open_mobile_viewer(self) -> None:
        import webbrowser

        if not MOBILE_VIEWER_URL:
            self.feedback.error("Mobile viewer is not available in this build.")
            return
        try:
            import pyperclip

            pyperclip.copy(MOBILE_VIEWER_URL)
            copied = True
        except Exception:
            copied = False
        webbrowser.open(MOBILE_VIEWER_URL)
        if copied:
            self.feedback.info("Mobile viewer opened — URL copied to clipboard.")
        else:
            self.feedback.info("Mobile viewer opened in your browser.")

    def _email_diagnostics(self) -> None:
        import webbrowser
        from urllib.parse import quote

        from skyadmin_pro.services.license import get_machine_id

        log_tail = ""
        try:
            log_path = Path.home() / ".skyadmin_pro" / "app.log"
            if log_path.exists():
                lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
                log_tail = "\n".join(lines[-40:])
        except Exception as e:
            import logging

            logging.error(f"UI Error: {e}")
        body = (
            f"Machine ID: {get_machine_id()}\n"
            f"Workspace: {self.app.paths.root}\n\n"
            "--- app.log (last 40 lines) ---\n"
            f"{log_tail}\n"
        )
        subject = "SkyAdmin Pro — Diagnostics"
        webbrowser.open(f"mailto:{OWNER_EMAIL}?subject={quote(subject)}&body={quote(body)}")

    def _open_activation(self) -> None:
        from skyadmin_pro.ui.activation import ActivationDialog

        ActivationDialog(
            self,
            db=self.db,
            allow_quit=False,
            on_activated=self._refresh_license_label,
        )
