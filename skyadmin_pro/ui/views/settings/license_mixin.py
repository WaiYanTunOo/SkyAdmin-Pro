"""Settings view mixins."""

from __future__ import annotations

from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from skyadmin_pro.config import (
    MOBILE_VIEWER_URL,
    OWNER_EMAIL,
)
from skyadmin_pro.ui.theme import TEXT_MUTED


class LicenseMixin:
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
        except Exception:
            pass
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
            allow_quit=False,
            on_activated=self._refresh_license_label,
        )

    def _activate_with_passcode(self) -> None:
        from skyadmin_pro.services.license import (
            _is_repair_activation,
            check_activation_usable,
            fetch_revocations,
            mark_used,
            report_activation_claim,
            requires_online_check,
            save_license_file,
        )
        from skyadmin_pro.ui.async_ui import run_background

        code = " ".join(self.passcode_var.get().split())
        if not code:
            self.feedback.error("Enter a passcode first.")
            return

        self.configure(cursor="watch")
        self.update_idletasks()

        def work() -> tuple[bool, str]:
            ok, msg, nonce = check_activation_usable(code)
            if not ok:
                return False, msg
            license_key: str | None = None
            if requires_online_check():
                net_ok, net_msg = fetch_revocations(timeout=6)
                if not net_ok:
                    return False, "Internet required to activate - " + net_msg.splitlines()[0]
                ok2, msg2, nonce2 = check_activation_usable(code)
                if not ok2:
                    return False, msg2
                claim_ok, claim_msg, license_key = report_activation_claim(
                    code,
                    allow_already_claimed=_is_repair_activation(code),
                )
                if not claim_ok:
                    return False, claim_msg
                ok, msg, nonce = ok2, msg2, nonce2
            to_save = (license_key or "").strip() or code
            save_license_file(to_save)
            if nonce:
                mark_used(nonce)
            return True, msg

        def on_success(result: tuple[bool, str]) -> None:
            ok, msg = result
            if ok:
                self._activation_ok(msg, "passcode")
            else:
                self._activation_fail(msg)

        run_background(
            self,
            work=work,
            on_success=on_success,
            on_error=self._activation_fail,
            finally_fn=lambda: self.configure(cursor=""),
            feedback=self.feedback,
        )

    def _activate_with_key(self) -> None:
        from skyadmin_pro.services.license import (
            _is_repair_activation,
            check_activation_usable,
            fetch_revocations,
            mark_used,
            report_activation_claim,
            requires_online_check,
            save_license_file,
        )
        from skyadmin_pro.ui.async_ui import run_background

        content = self.key_paste_var.get().strip()
        if not content:
            self.feedback.error("Paste a license key first.")
            return

        self.configure(cursor="watch")
        self.update_idletasks()

        def work() -> tuple[bool, str]:
            ok, msg, nonce = check_activation_usable(content)
            if not ok:
                return False, msg
            license_key: str | None = None
            if requires_online_check():
                net_ok, net_msg = fetch_revocations(timeout=6)
                if not net_ok:
                    return False, "Internet required to activate - " + net_msg.splitlines()[0]
                ok2, msg2, nonce2 = check_activation_usable(content)
                if not ok2:
                    return False, msg2
                claim_ok, claim_msg, license_key = report_activation_claim(
                    content,
                    allow_already_claimed=_is_repair_activation(content),
                )
                if not claim_ok:
                    return False, claim_msg
                ok, msg, nonce = ok2, msg2, nonce2
            to_save = (license_key or "").strip() or content
            save_license_file(to_save)
            if nonce:
                mark_used(nonce)
            return True, msg

        def on_success(result: tuple[bool, str]) -> None:
            ok, msg = result
            if ok:
                self._activation_ok(msg, "key")
            else:
                self._activation_fail(msg)

        run_background(
            self,
            work=work,
            on_success=on_success,
            on_error=self._activation_fail,
            finally_fn=lambda: self.configure(cursor=""),
            feedback=self.feedback,
        )

    def _activate_pasted(self) -> None:
        """Activate from the single paste field (license key or SKYPASS1 passcode)."""
        raw = self.key_paste_var.get().strip()
        if not raw:
            self.feedback.error("Paste a license key or passcode first.")
            return
        if raw.upper().startswith("SKYPASS1:"):
            self.passcode_var.set(raw)
            self._activate_with_passcode()
        else:
            self._activate_with_key()

    def _activation_fail(self, msg) -> None:
        self.configure(cursor="")
        self.feedback.error(msg.splitlines()[0])

    def _activation_ok(self, msg, kind) -> None:
        self.configure(cursor="")
        self.passcode_var.set("")
        self.key_paste_var.set("")
        self._refresh_license_label()
        self.feedback.success(f"✓ {msg.splitlines()[0]} — activated.")
        self.app.set_status(f"License activated via {kind}.")
        self.app.refresh_sidebar_status()

    def _after(self, fn) -> None:
        from skyadmin_pro.ui.async_ui import run_on_main

        run_on_main(self, fn, feedback=self.feedback)

    def _begin_license_background(self, action: str, status: str) -> None:
        """Disable sync/update controls while a background license task runs."""
        self._license_bg_action = action
        self.configure(cursor="watch")
        self.feedback.info(status)
        sync_btn = getattr(self, "sync_now_btn", None)
        upd_btn = getattr(self, "check_updates_btn", None)
        if sync_btn is not None:
            sync_btn.configure(
                state="disabled",
                text="Syncing…" if action == "sync" else sync_btn.cget("text"),
            )
        if upd_btn is not None:
            upd_btn.configure(
                state="disabled",
                text="Checking…" if action == "updates" else upd_btn.cget("text"),
            )

    def _end_license_background(self) -> None:
        self.configure(cursor="")
        sync_btn = getattr(self, "sync_now_btn", None)
        upd_btn = getattr(self, "check_updates_btn", None)
        if sync_btn is not None:
            sync_btn.configure(state="normal", text="Sync now")
        if upd_btn is not None:
            upd_btn.configure(state="normal", text="Check updates")

    def _format_data_sync_status(self) -> str:
        from skyadmin_pro.config import SETTING_SYNC_LAST_PULL
        from skyadmin_pro.services.data_sync import is_data_sync_enabled

        if not is_data_sync_enabled(self.app.db):
            return "Cloud data sync: off (use encrypted backup for a second PC)"
        last = (self.app.db.get_setting(SETTING_SYNC_LAST_PULL) or "").strip()
        conflicts = self.app.db.count_sync_conflicts()
        parts: list[str] = []
        if last:
            display = last.replace("T", " ")[:19]
            parts.append(f"Last data sync: {display}")
        else:
            parts.append("Data sync: never")
        if conflicts:
            parts.append(f"{conflicts} sync conflict(s) logged")
        return " · ".join(parts)

    def _run_integrity_check(self) -> None:
        ok = self.app.db.quick_check()
        self._refresh_integrity_banner()
        if ok:
            messagebox.showinfo(
                "Database integrity",
                "✓ quick_check passed — your local database looks healthy.",
                parent=self.winfo_toplevel(),
            )
            self.feedback.success("Database integrity check passed.")
            return
        messagebox.showwarning(
            "Database integrity",
            "✗ Integrity check failed.\n\n"
            "Restore from an encrypted backup (.skybackup) or a daily snapshot in "
            f"{self.app.db.db_file.parent / 'backups'} if data looks wrong.",
            parent=self.winfo_toplevel(),
        )
        self.feedback.error("Database integrity check failed — see dialog.")

    def _refresh_integrity_banner(self) -> None:
        banner = getattr(self, "integrity_banner", None)
        if banner is None:
            return
        try:
            ok = self.app.db.quick_check()
        except Exception:
            banner.configure(text="⚠ Database integrity check could not run — contact support if data looks wrong.")
            banner.grid()
            return
        if ok:
            banner.configure(text="")
            banner.grid_remove()
        else:
            banner.configure(
                text=(
                    "⚠ Database integrity check failed. Restore from an encrypted backup "
                    "or a daily snapshot before continuing heavy work."
                )
            )
            banner.grid()

    def _refresh_license_label(self) -> None:
        try:
            from skyadmin_pro.services.license import (
                get_daily_sync_status,
                get_machine_id,
                license_expiry_text,
                verify_license,
            )

            ok, _msg = verify_license()
            if ok:
                self.license_label.configure(
                    text=f"✓ License active — {license_expiry_text()}  ·  Machine ID: {get_machine_id()}",
                    text_color=("#15803d", "#4ade80"),
                )
            else:
                self.license_label.configure(
                    text=f"✗ No valid license  ·  Machine ID: {get_machine_id()}",
                    text_color=("#b45309", "#fbbf24"),
                )
            # Online check — warn only when overdue (no countdown when OK).
            try:
                sync_ok, sync_msg = get_daily_sync_status()
                if sync_ok:
                    self.daily_sync_label.configure(text="")
                else:
                    self.daily_sync_label.configure(
                        text="⚠ " + sync_msg,
                        text_color=("#b45309", "#fbbf24"),
                    )
                self.data_sync_label.configure(text=self._format_data_sync_status())
                count = self.app.db.count_sync_conflicts()
                self.conflicts_btn.configure(
                    state="normal" if count else "disabled",
                    text=f"Conflicts ({count})" if count else "Conflicts",
                )
            except Exception:
                self.daily_sync_label.configure(text="")
                try:
                    self.data_sync_label.configure(text="")
                except Exception:
                    pass
        except Exception:
            self.license_label.configure(text="License: unavailable")
            try:
                self.daily_sync_label.configure(text="")
                self.data_sync_label.configure(text="")
            except Exception:
                pass

    def _check_for_updates(self) -> None:
        from skyadmin_pro.services.license import check_for_updates
        from skyadmin_pro.ui.async_ui import run_background

        self._begin_license_background("updates", "Checking for updates…")
        self.daily_sync_label.configure(text="Checking for updates…", text_color=TEXT_MUTED)

        def work() -> tuple[bool, str, dict | None]:
            try:
                return check_for_updates(timeout=8)
            except Exception as exc:
                return False, str(exc), None

        def on_success(result: tuple[bool, str, dict | None]) -> None:
            ok, msg, info = result
            self._refresh_license_label()
            self._refresh_update_banner()
            if info:
                ver = info.get("version", "?")
                self.feedback.success(f"Update available: v{ver}")
            elif ok:
                self.feedback.info("You are on the latest published version.")
            else:
                self.feedback.error(msg.splitlines()[0])

        run_background(
            self,
            work=work,
            on_success=on_success,
            on_error=lambda err: self.feedback.error(err.splitlines()[0]),
            finally_fn=self._end_license_background,
            feedback=self.feedback,
        )

    def _open_sync_conflicts(self) -> None:
        from skyadmin_pro.ui.views.settings.sync_conflicts_dialog import open_sync_conflicts_dialog

        open_sync_conflicts_dialog(
            self,
            db=self.app.db,
            feedback=self.feedback,
            on_cleared=self._refresh_license_label,
        )

    def _on_data_sync_toggle(self) -> None:
        from skyadmin_pro.config import SETTING_DATA_SYNC_ENABLED

        enabled = bool(self.data_sync_var.get())
        self.app.db.set_setting(SETTING_DATA_SYNC_ENABLED, "1" if enabled else "0")
        self._refresh_license_label()
        if enabled:
            self.feedback.info("Cloud data sync enabled for this licensed PC only.")
        else:
            self.feedback.info("Cloud data sync disabled — use encrypted backup for a second PC.")

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
        # Read from the app itself (embedded) so it always works in the
        # packaged exe; fall back to the shipped LICENSE file if present.
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
        top.attributes("-topmost", True)
        from skyadmin_pro.ui.widgets import make_modal

        make_modal(top)
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(0, weight=1)
        box = ctk.CTkTextbox(top, wrap="word")
        box.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        box.insert("1.0", text)
        box.configure(state="disabled")
        ctk.CTkButton(top, text="Close", width=110, command=top.destroy).grid(row=1, column=0, pady=(0, 16))
