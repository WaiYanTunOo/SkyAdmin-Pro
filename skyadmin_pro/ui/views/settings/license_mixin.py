"""Settings view mixins."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from skyadmin_pro.config import (
    CHECKLIST_TEMPLATES,
    DEFAULT_COLOR_THEME,
    DEFAULT_PORTAL_URL,
    MOBILE_VIEWER_URL,
    OWNER_EMAIL,
    PRICING_DEFAULT_SERVICE,
    SERVICE_TYPES,
    SETTING_APPEARANCE_MODE,
    SETTING_COLOR_THEME,
    SETTING_PORTAL_URL,
    SETTING_WORKSPACE_CUSTOM,
    SETTING_WORKSPACE_ROOT,
    pricing_uses_transaction_ranges,
)
from skyadmin_pro.paths import WorkspacePaths
from skyadmin_pro.services.data_hygiene import run_data_hygiene
from skyadmin_pro.services.file_ops import open_in_file_manager
from skyadmin_pro.services.workflow import normalize_portal_url, repair_client_workspaces
from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import FeedbackLabel, bind_wrap_label, make_modal, themed_entry


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
            self.update_frame.grid(row=0, column=0, sticky="ew", pady=(0, 14))
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
        import threading

        from skyadmin_pro.services.license import (
            check_activation_usable,
            fetch_revocations,
            mark_used,
            report_activation_claim,
            requires_online_check,
            save_license_file,
            _is_repair_activation,
        )

        code = " ".join(self.passcode_var.get().split())
        if not code:
            self.feedback.error("Enter a passcode first.")
            return

        self.feedback.info("Verifying passcode…")
        self.configure(cursor="watch")
        self.update_idletasks()

        def worker():
            try:
                ok, msg, nonce = check_activation_usable(code)
                if not ok:
                    self._after(lambda: self._activation_fail(msg))
                    return
                if requires_online_check():
                    net_ok, net_msg = fetch_revocations(timeout=6)
                    if not net_ok:
                        self._after(
                            lambda: self._activation_fail("Internet required to activate - " + net_msg.splitlines()[0])
                        )
                        return
                    ok2, msg2, nonce2 = check_activation_usable(code)
                    if not ok2:
                        self._after(lambda: self._activation_fail(msg2))
                        return
                    claim_ok, claim_msg = report_activation_claim(
                        code,
                        allow_already_claimed=_is_repair_activation(code),
                    )
                    if not claim_ok:
                        self._after(lambda: self._activation_fail(claim_msg))
                        return
                    ok, msg, nonce = ok2, msg2, nonce2
                save_license_file(code)
                if nonce:
                    mark_used(nonce)
                self._after(lambda: self._activation_ok(msg, "passcode"))
            except Exception as exc:
                self._after(lambda: self._activation_fail(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _activate_with_key(self) -> None:
        import threading

        from skyadmin_pro.services.license import (
            check_activation_usable,
            fetch_revocations,
            mark_used,
            report_activation_claim,
            requires_online_check,
            save_license_file,
            _is_repair_activation,
        )

        content = self.key_paste_var.get().strip()
        if not content:
            self.feedback.error("Paste a license key first.")
            return

        self.feedback.info("Verifying license key…")
        self.configure(cursor="watch")
        self.update_idletasks()

        def worker():
            try:
                ok, msg, nonce = check_activation_usable(content)
                if not ok:
                    self._after(lambda: self._activation_fail(msg))
                    return
                if requires_online_check():
                    net_ok, net_msg = fetch_revocations(timeout=6)
                    if not net_ok:
                        self._after(
                            lambda: self._activation_fail("Internet required to activate - " + net_msg.splitlines()[0])
                        )
                        return
                    ok2, msg2, nonce2 = check_activation_usable(content)
                    if not ok2:
                        self._after(lambda: self._activation_fail(msg2))
                        return
                    claim_ok, claim_msg = report_activation_claim(
                        content,
                        allow_already_claimed=_is_repair_activation(content),
                    )
                    if not claim_ok:
                        self._after(lambda: self._activation_fail(claim_msg))
                        return
                    ok, msg, nonce = ok2, msg2, nonce2
                save_license_file(content)
                if nonce:
                    mark_used(nonce)
                self._after(lambda: self._activation_ok(msg, "key"))
            except Exception as exc:
                self._after(lambda: self._activation_fail(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

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
        def wrapped() -> None:
            if not self.winfo_exists():
                return
            fn()

        try:
            self.after(0, wrapped)
        except Exception:
            pass

    def _format_data_sync_status(self) -> str:
        from skyadmin_pro.config import SETTING_SYNC_LAST_PULL

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
            banner.configure(
                text="⚠ Database integrity check could not run — contact support if data looks wrong."
            )
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
            # Daily online status
            try:
                sync_ok, sync_msg = get_daily_sync_status()
                self.daily_sync_label.configure(
                    text=("✓ " if sync_ok else "⚠ ") + sync_msg,
                    text_color=("#15803d", "#4ade80") if sync_ok else ("#b45309", "#fbbf24"),
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
        import threading

        from skyadmin_pro.services.license import check_for_updates

        self.feedback.info("Checking for updates…")
        self.daily_sync_label.configure(text="Checking for updates…", text_color=TEXT_MUTED)
        btn = getattr(self, "check_updates_btn", None)
        if btn is not None:
            btn.configure(state="disabled")
        self.configure(cursor="watch")

        def worker() -> None:
            try:
                ok, msg, info = check_for_updates(timeout=8)
            except Exception as exc:
                ok, msg, info = False, str(exc), None

            def done() -> None:
                if not self.winfo_exists():
                    return
                self.configure(cursor="")
                if btn is not None:
                    btn.configure(state="normal")
                self._refresh_license_label()
                self._refresh_update_banner()
                if info:
                    ver = info.get("version", "?")
                    self.feedback.success(f"Update available: v{ver}")
                elif ok:
                    self.feedback.info("You are on the latest published version.")
                else:
                    self.feedback.error(msg.splitlines()[0])

            self._after(done)

        threading.Thread(target=worker, daemon=True).start()

    def _open_sync_conflicts(self) -> None:
        rows = self.app.db.list_sync_conflicts(limit=200)
        if not rows:
            messagebox.showinfo(
                "Sync conflicts",
                "No sync conflicts logged.\n\n"
                "Conflicts are recorded when the server has older data than your PC "
                "(last-write-wins keeps your local copy).",
                parent=self.winfo_toplevel(),
            )
            return

        top = ctk.CTkToplevel(self)
        top.title("SkyAdmin Pro — Sync conflicts")
        top.geometry("820x480")
        top.minsize(640, 360)
        make_modal(top)
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            top,
            text=(
                f"{len(rows)} conflict(s) logged — your local data was kept. "
                "These rows were not overwritten because your copy is newer."
            ),
            anchor="w",
            justify="left",
            text_color=TEXT_MUTED,
            wraplength=760,
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))

        columns = ("logged", "table", "global_id", "direction", "local", "remote")
        tree = ThemedTreeview(
            top,
            columns=columns,
            show="headings",
            height=14,
        )
        tree.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 8))
        headings = {
            "logged": "Logged",
            "table": "Table",
            "global_id": "Global ID",
            "direction": "Dir",
            "local": "Local updated",
            "remote": "Remote updated",
        }
        widths = {"logged": 130, "table": 110, "global_id": 200, "direction": 50, "local": 130, "remote": 130}
        for col in columns:
            tree.heading(col, text=headings[col])
            tree.column(col, width=widths.get(col, 100), anchor="w")

        for row in rows:
            tree.insert(
                "",
                "end",
                values=(
                    str(row.get("logged_at") or "")[:19],
                    row.get("table_name") or "",
                    row.get("global_id") or "",
                    row.get("direction") or "",
                    str(row.get("local_updated_at") or "")[:19],
                    str(row.get("remote_updated_at") or "")[:19],
                ),
            )

        actions = ctk.CTkFrame(top, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))
        actions.grid_columnconfigure(0, weight=1)

        def _clear() -> None:
            if not messagebox.askyesno(
                "Clear conflict log",
                f"Remove all {len(rows)} logged conflict(s)?\n\n"
                "This only clears the audit log — your data is unchanged.",
                parent=top,
            ):
                return
            cleared = self.app.db.clear_sync_conflicts()
            self.feedback.success(f"Cleared {cleared} sync conflict log entries.")
            self._refresh_license_label()
            top.destroy()

        ctk.CTkButton(actions, text="Clear log", width=100, fg_color="#b45309", command=_clear).pack(
            side="left"
        )
        ctk.CTkButton(actions, text="Close", width=90, command=top.destroy).pack(side="right")

    def _sync_now(self) -> None:
        import threading

        from skyadmin_pro.services.data_sync import sync_data
        from skyadmin_pro.services.license import fetch_revocations

        self.feedback.info("Syncing license + data…")
        self.daily_sync_label.configure(text="Syncing…", text_color=TEXT_MUTED)
        self.data_sync_label.configure(text="")
        sync_btn = getattr(self, "sync_now_btn", None)
        if sync_btn is not None:
            sync_btn.configure(state="disabled")
        self.configure(cursor="watch")

        def worker():
            try:
                lic_ok, lic_msg = fetch_revocations(timeout=6)
                data_ok, data_msg = sync_data(self.app.db, timeout=25)
                ok = lic_ok and data_ok
                if lic_ok and data_ok:
                    msg = f"{lic_msg.splitlines()[0]} · {data_msg}"
                elif not lic_ok:
                    msg = lic_msg
                else:
                    msg = data_msg
            except Exception as exc:
                ok, msg = False, str(exc)

            def done():
                if not self.winfo_exists():
                    return
                self.configure(cursor="")
                if sync_btn is not None:
                    sync_btn.configure(state="normal")
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

            self._after(done)

        threading.Thread(target=worker, daemon=True).start()

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

