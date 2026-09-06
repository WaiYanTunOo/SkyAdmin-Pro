"""Online-assisted license activation + pricing dialog — Sky Creation Innovations.

Customer flow: unlicensed/expired launch → pricing packages shown → customer
enters their email and requests a code (email / WhatsApp) → owner replies
with a signed code from the phone generator → paste → activated instantly.
"""

from __future__ import annotations

import logging
from urllib.parse import quote
from webbrowser import open as _open_url

import customtkinter as ctk

from skyadmin_pro.config import (
    LEGAL_LICENSE_TEXT,
    OWNER_EMAIL,
    OWNER_WHATSAPP_DISPLAY,
    OWNER_WHATSAPP_NUMBER,
    PRICING_OVER_YEAR_TEXT,
    PRICING_TIERS,
)
from skyadmin_pro.services.license import (
    activation_request_message,
    check_activation_usable,
    get_machine_id,
)  # noqa: F401 (fetch_revocations used inside _activate worker)
from skyadmin_pro.ui.theme import (
    CARD_RADIUS,
    FEEDBACK_ERROR,
    FEEDBACK_INFO,
    FEEDBACK_SUCCESS,
    HEADER_TITLE_SIZE,
    TEXT_MUTED,
)
from skyadmin_pro.ui.widgets import bind_wrap_label, themed_entry, themed_scrollable_frame, themed_textbox


def open_whatsapp_chat(message: str = "") -> None:
    url = f"https://wa.me/{OWNER_WHATSAPP_NUMBER}?text={quote(message or 'Hello Sky Creation Innovations')}"
    _open_url(url)


class ActivationDialog(ctk.CTkToplevel):
    """Pricing + modal activation window; usable standalone (pre-app)."""

    def __init__(
        self,
        master=None,
        *,
        on_activated=None,
        allow_quit: bool = True,
        on_close_request=None,
    ) -> None:
        if master is not None:
            super().__init__(master)
        else:
            super().__init__()
        self.title("SkyAdmin Pro — Pricing & Activation")
        self.geometry("620x740")
        self.minsize(560, 560)
        self.attributes("-topmost", True)
        self.configure(fg_color=("gray94", "gray12"))
        if master is not None:
            self.transient(master.winfo_toplevel())
        self._on_activated = on_activated
        self._on_close_request = on_close_request
        self._activated = False
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        machine_id = get_machine_id()

        # Scrollable content — status + actions stay fixed below so feedback is visible.
        scroll = themed_scrollable_frame(self)
        scroll.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 0))
        scroll.grid_columnconfigure(0, weight=1)
        body = scroll

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))
        footer.grid_columnconfigure(0, weight=1)

        # Header — includes remaining days when relevant
        ctk.CTkLabel(
            body,
            text="Pricing & Activation",
            font=ctk.CTkFont(size=HEADER_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(18, 0))

        from skyadmin_pro.services.license import license_time_left_text

        left = license_time_left_text()
        if left == "Not activated":
            sub = "Choose a package to activate this copy of SkyAdmin Pro."
        elif left.startswith("Active — no expiry"):
            sub = left
        elif left.startswith("Expired"):
            sub = f"Your license {left.lower()}. Choose a package to continue."
        elif left.startswith("Active —"):
            sub = left.replace("Active —", "License active —", 1)
        else:
            sub = left
        ctk.CTkLabel(body, text=sub, text_color=TEXT_MUTED, anchor="w").grid(
            row=1, column=0, sticky="ew", padx=16, pady=(2, 10)
        )

        # ---- Pricing packages ----
        self._price_card = ctk.CTkFrame(body, corner_radius=CARD_RADIUS)
        self._price_card.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
        self._over_year_text = PRICING_OVER_YEAR_TEXT
        self._render_pricing_tiers(PRICING_TIERS)
        self._refresh_pricing_from_api()

        # ---- Machine ID card ----
        mid_card = ctk.CTkFrame(body, corner_radius=CARD_RADIUS)
        mid_card.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))
        mid_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(mid_card, text="Your Machine ID", anchor="w", text_color=TEXT_MUTED).grid(
            row=0, column=0, sticky="w", padx=16, pady=(12, 2)
        )
        ctk.CTkLabel(
            mid_card,
            text=machine_id,
            font=ctk.CTkFont(size=19, weight="bold"),
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=16)
        ctk.CTkButton(
            mid_card,
            text="Copy Machine ID",
            width=160,
            fg_color="transparent",
            border_width=1,
            command=self._copy_mid,
        ).grid(row=2, column=0, sticky="w", padx=16, pady=(6, 12))

        # ---- Step 1: email request ----
        ctk.CTkLabel(
            body,
            text="1. Enter your email — we reply with your code:",
            anchor="w",
        ).grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 4))
        self.email_var = ctk.StringVar()
        themed_entry(
            body,
            textvariable=self.email_var,
            placeholder_text="yourname@gmail.com",
        ).grid(row=5, column=0, sticky="ew", padx=16)
        req_row = ctk.CTkFrame(body, fg_color="transparent")
        req_row.grid(row=6, column=0, sticky="ew", padx=16, pady=(8, 0))
        req_row.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(req_row, text="Request Code by Email", height=38, command=self._request_email).grid(
            row=0, column=0, sticky="ew"
        )
        ctk.CTkButton(
            req_row,
            text="Discuss on WhatsApp",
            height=38,
            fg_color=("#0f766e", "#14b8a6"),
            hover_color="#075E54",
            command=lambda: open_whatsapp_chat(activation_request_message(self._customer_email())),
        ).grid(row=1, column=0, sticky="ew", pady=(6, 0))
        contact_hint = ctk.CTkLabel(
            req_row,
            text=f"Email: {OWNER_EMAIL}   ·   WhatsApp: {OWNER_WHATSAPP_DISPLAY}",
            text_color=TEXT_MUTED,
            anchor="w",
            justify="left",
        )
        contact_hint.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        bind_wrap_label(contact_hint, req_row, pad=16)

        # ---- Step 2: paste code ----
        ctk.CTkLabel(
            body,
            text="2. Paste the License Key or Passcode you received:",
            anchor="w",
        ).grid(row=7, column=0, sticky="ew", padx=16, pady=(14, 4))
        self.key_box = themed_textbox(body, height=80, wrap="char")
        self.key_box.grid(row=8, column=0, sticky="ew", padx=16, pady=(0, 8))
        self.key_box.bind("<Control-Return>", lambda _e: self._activate())
        self.key_box.bind("<Return>", lambda _e: self._activate())

        self.status = ctk.CTkLabel(
            footer,
            text="Paste your license key or passcode above, then click Activate Now.",
            anchor="w",
            justify="left",
            text_color=TEXT_MUTED,
        )
        self.status.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        bind_wrap_label(self.status, footer, pad=0)

        self.activate_btn = ctk.CTkButton(footer, text="Activate Now", height=42, command=self._activate)
        self.activate_btn.grid(row=1, column=0, sticky="ew")
        bottom = ctk.CTkFrame(footer, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.continue_btn = ctk.CTkButton(
            bottom,
            text="Continue to App",
            height=34,
            state="disabled",
            command=self._continue,
        )
        self.continue_btn.pack(side="left")
        ctk.CTkButton(
            bottom,
            text="License",
            height=34,
            fg_color="transparent",
            border_width=1,
            command=self._show_license_text,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            bottom,
            text="Disclaimer",
            height=34,
            fg_color="transparent",
            border_width=1,
            command=self._show_disclaimer_text,
        ).pack(side="left", padx=(6, 0))
        if allow_quit:
            ctk.CTkButton(
                bottom,
                text="Quit",
                height=34,
                fg_color="transparent",
                border_width=1,
                command=self._quit,
            ).pack(side="right")

        self.bind("<Escape>", lambda _e: self._close())
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(100, self._focus_key_box)

    # ------------------------------------------------------------------ #
    def _render_pricing_tiers(self, tiers: tuple[tuple[str, int, int], ...]) -> None:
        card = self._price_card
        for child in card.winfo_children():
            child.destroy()
        card.grid_columnconfigure((0, 1), weight=1, uniform="tiers")
        ctk.CTkLabel(
            card,
            text="Packages",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 4))
        for i, (label, _days, baht) in enumerate(tiers):
            r, c = divmod(i, 2)
            tier = ctk.CTkFrame(card, corner_radius=10)
            tier.grid(row=r + 1, column=c, sticky="nsew", padx=8, pady=4)
            ctk.CTkLabel(tier, text=label, font=ctk.CTkFont(size=14, weight="bold")).pack(
                anchor="w", padx=12, pady=(8, 0)
            )
            ctk.CTkLabel(
                tier,
                text=f"{baht:,} Baht",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="#2563eb" if ctk.get_appearance_mode() == "Light" else "#60a5fa",
            ).pack(anchor="w", padx=12, pady=(0, 8))
        rows_used = (len(tiers) + 1) // 2
        over = ctk.CTkFrame(card, corner_radius=10, fg_color=("gray90", "gray20"))
        over.grid(row=rows_used + 1, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 12))
        over.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(over, text=self._over_year_text, anchor="w").grid(row=0, column=0, sticky="w", padx=12, pady=10)
        ctk.CTkButton(
            over,
            text="WhatsApp us",
            width=130,
            height=30,
            fg_color=("#0f766e", "#14b8a6"),
            hover_color="#075E54",
            command=lambda: open_whatsapp_chat(
                f"SkyAdmin Pro — I'm interested in a license over 1 year.\nMachine ID: {get_machine_id()}"
            ),
        ).grid(row=0, column=1, sticky="e", padx=12, pady=6)
        ctk.CTkLabel(
            card,
            text=(
                "Payment: contact us on WhatsApp or email —\n"
                f"{OWNER_WHATSAPP_DISPLAY} · {OWNER_EMAIL}\n"
                "After payment you receive a one-time activation code."
            ),
            justify="center",
            text_color=TEXT_MUTED,
        ).grid(row=rows_used + 2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 12))

    def _refresh_pricing_from_api(self) -> None:
        import threading

        def worker() -> None:
            from skyadmin_pro.services.remote_pricing import fetch_pricing_tiers, fetch_signing_key_status

            tiers, over_year = fetch_pricing_tiers()
            key_ok, key_msg = fetch_signing_key_status()

            def done() -> None:
                if not self.winfo_exists():
                    return
                self._over_year_text = over_year
                self._render_pricing_tiers(tiers)
                if not key_ok and key_msg:
                    self._set_status(f"⚠ {key_msg}", "error")

            self._schedule_ui(done)

        threading.Thread(target=worker, daemon=True).start()

    def _focus_key_box(self) -> None:
        try:
            self.key_box.focus_set()
        except Exception:  # defensive: Tk teardown/callback
            pass

    def _schedule_ui(self, fn) -> None:
        """Run *fn* on the Tk main thread (required after worker threads)."""
        try:
            self.after(0, fn)
        except Exception:
            try:
                fn()
            except Exception:  # defensive: Tk teardown/callback
                pass

    def _customer_email(self) -> str:
        return " ".join(self.email_var.get().split())

    def _copy_mid(self) -> None:
        mid = get_machine_id()
        try:
            import pyperclip

            pyperclip.copy(mid)
        except Exception:
            try:
                top = self.winfo_toplevel()
                top.clipboard_clear()
                top.clipboard_append(mid)
            except Exception:  # defensive: Tk teardown/callback
                pass
        self._set_status("Machine ID copied.", "info")

    def _request_email(self) -> None:
        email = self._customer_email()
        if not email or "@" not in email or "." not in email.split("@")[-1]:
            self._set_status("Enter a valid email first — the code is replied there.", "error")
            return
        subject = "SkyAdmin Pro — License Request"
        body = activation_request_message(email)
        url = f"mailto:{OWNER_EMAIL}?subject={quote(subject)}&body={quote(body)}"
        _open_url(url)
        try:
            import pyperclip

            pyperclip.copy(body)
        except Exception:  # defensive: Tk teardown/callback
            pass
        self._set_status(
            "Email opened — press Send. We reply to your email with the code,"
            " then paste it below. (Request also copied to clipboard.)",
            "info",
        )

    def _activate(self) -> None:
        if getattr(self, "_activating", False):
            return
        try:
            content = "".join(self.key_box.get("1.0", "end").split())
            if not content:
                self._set_status("✗ Paste the license key or passcode first.", "error")
                return

            self._set_status("Checking license…", "info")
            self.update_idletasks()

            ok, msg, nonce = check_activation_usable(content)
            if not ok:
                self._set_status(f"✗ {msg}", "error")
                return

            from skyadmin_pro.services.license import (
                _is_repair_activation,
                fetch_revocations,
                mark_used,
                report_activation_claim,
                requires_online_check,
                save_license_file,
            )

            needs_online = requires_online_check()
            self._activating = True
            self.activate_btn.configure(state="disabled", text="Checking…")
            self.update_idletasks()

            def _finish(ok_final: bool, message: str, nonce_final: str | None, license_key: str | None = None) -> None:
                self._activating = False
                self.activate_btn.configure(state="normal", text="Activate Now")
                if not ok_final:
                    self._set_status(f"✗ {message}", "error")
                    return
                to_save = (license_key or "").strip() or content
                save_license_file(to_save)
                if nonce_final:
                    mark_used(nonce_final)
                self._set_status(f"✓ {message} Activation complete.", "success")
                self.continue_btn.configure(state="normal")
                if self._on_activated is not None:
                    try:
                        self._on_activated()
                    except Exception:
                        logging.getLogger(__name__).warning("Activation callback failed", exc_info=True)

            if not needs_online:
                _finish(True, msg, nonce, None)
                return

            self._set_status("Checking license online…", "info")

            def worker() -> None:
                result_ok = False
                result_msg = "Activation failed."
                result_nonce: str | None = None
                result_license_key: str | None = None
                try:
                    net_ok, net_msg = fetch_revocations()
                    if not net_ok:
                        result_msg = "Internet connection is required to activate. Please connect and try again."
                    else:
                        ok2, msg2, n2 = check_activation_usable(content)
                        if not ok2:
                            result_msg = msg2
                        else:
                            claim_ok, claim_msg, license_key = report_activation_claim(
                                content,
                                allow_already_claimed=_is_repair_activation(content),
                            )
                            if not claim_ok:
                                result_msg = claim_msg
                            else:
                                result_ok, result_msg, result_nonce, result_license_key = (
                                    ok2,
                                    msg2,
                                    n2,
                                    license_key,
                                )
                except Exception as exc:
                    result_msg = f"Activation error: {exc}"

                def done() -> None:
                    if not self.winfo_exists():
                        return
                    _finish(result_ok, result_msg, result_nonce, result_license_key)

                self._schedule_ui(done)

            import threading

            threading.Thread(target=worker, daemon=True).start()
        except Exception as exc:
            self._activating = False
            self.activate_btn.configure(state="normal", text="Activate Now")
            self._set_status(f"✗ Activation error: {exc}", "error")

    def _show_license_text(self) -> None:
        """Full agreement from inside the app (works in packaged exe)."""
        self._show_legal("License Agreement", LEGAL_LICENSE_TEXT)

    def _show_disclaimer_text(self) -> None:
        from skyadmin_pro.config import LEGAL_DISCLAIMER_TEXT

        self._show_legal("Disclaimer", LEGAL_DISCLAIMER_TEXT)

    def _show_legal(self, title: str, text: str) -> None:
        top = ctk.CTkToplevel(self)
        top.title(f"SkyAdmin Pro — {title}")
        top.geometry("720x560")
        top.transient(self.winfo_toplevel())
        top.attributes("-topmost", True)
        try:
            top.grab_set()
        except Exception:  # defensive: Tk teardown/callback
            pass
        top.bind("<Escape>", lambda _e: top.destroy())
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(0, weight=1)
        box = ctk.CTkTextbox(top, wrap="word")
        box.grid(row=0, column=0, sticky="nsew", padx=14, pady=(14, 6))
        box.insert("1.0", text)
        box.configure(state="disabled")
        ctk.CTkButton(top, text="Close", width=110, command=top.destroy).grid(row=1, column=0, pady=(0, 14))

    def _continue(self) -> None:
        self._close()

    def _quit(self) -> None:
        self._close()

    def _close(self) -> None:
        try:
            self.destroy()
        finally:
            if self._on_close_request is not None:
                try:
                    self._on_close_request()
                except Exception:  # defensive: Tk teardown/callback
                    pass

    def _set_status(self, text: str, kind: str) -> None:
        color = {
            "success": FEEDBACK_SUCCESS,
            "error": FEEDBACK_ERROR,
            "info": FEEDBACK_INFO,
        }[kind]
        self.status.configure(text=text, text_color=color)


def run_activation_standalone() -> bool:
    """Pre-app activation loop. Returns True when licensed."""
    from skyadmin_pro.services.license import verify_license

    ok, _msg = verify_license()
    if ok:
        return True

    app = ctk.CTk()
    app.withdraw()

    def _finish() -> None:
        try:
            app.quit()
        except Exception:  # defensive: Tk teardown/callback
            pass

    dialog = ActivationDialog(app, allow_quit=True, on_close_request=_finish)
    try:
        dialog.attributes("-topmost", True)
        dialog.lift()
        dialog.focus_force()
    except Exception:  # defensive: Tk teardown/callback
        pass
    app.mainloop()
    try:
        dialog.destroy()
    except Exception:  # defensive: Tk teardown/callback
        pass
    try:
        app.destroy()
    except Exception:  # defensive: Tk teardown/callback
        pass
    ok, _msg = verify_license()
    return ok
