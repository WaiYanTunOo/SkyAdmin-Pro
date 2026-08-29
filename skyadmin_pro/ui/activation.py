"""Online-assisted license activation + pricing dialog — Sky Creation Innovations.

Customer flow: unlicensed/expired launch → pricing packages shown → customer
enters their email and requests a code (email / WhatsApp) → owner replies
with a signed code from the phone generator → paste → activated instantly.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
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
    fetch_revocations,
    get_machine_id,
    license_remaining_days,
    mark_used,
    save_license_file,
    verify_key_text,
)  # noqa: F401 (fetch_revocations used inside _activate worker)
from skyadmin_pro.ui.theme import (
    CARD_RADIUS,
    FEEDBACK_ERROR,
    FEEDBACK_INFO,
    FEEDBACK_SUCCESS,
    HEADER_TITLE_SIZE,
    TEXT_MUTED,
)
from skyadmin_pro.ui.widgets import make_modal  # noqa: F401 (dialog helper)


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

        # Everything scrolls vertically (Excel-like comfort on small screens).
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        body = scroll

        # Header — includes remaining days when relevant
        ctk.CTkLabel(
            body, text="Pricing & Activation",
            font=ctk.CTkFont(size=HEADER_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(18, 0))

        days = license_remaining_days()
        if days is not None and days < 0:
            sub = f"Your license expired {abs(days)} day(s) ago. Choose a package to continue."
        elif days is None:
            sub = "Choose a package to activate this copy of SkyAdmin Pro."
        else:
            sub = f"License active — {days} day(s) remaining."
        ctk.CTkLabel(body, text=sub, text_color=TEXT_MUTED, anchor="w").grid(
            row=1, column=0, sticky="ew", padx=16, pady=(2, 10)
        )

        # ---- Pricing packages ----
        price_card = ctk.CTkFrame(body, corner_radius=CARD_RADIUS)
        price_card.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
        price_card.grid_columnconfigure((0, 1), weight=1, uniform="tiers")
        ctk.CTkLabel(
            price_card, text="Packages", anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 4))
        for i, (label, _days, baht) in enumerate(PRICING_TIERS):
            r, c = divmod(i, 2)
            tier = ctk.CTkFrame(price_card, corner_radius=10)
            tier.grid(row=r + 1, column=c, sticky="nsew", padx=8, pady=4)
            ctk.CTkLabel(tier, text=label, font=ctk.CTkFont(size=14, weight="bold")).pack(
                anchor="w", padx=12, pady=(8, 0)
            )
            ctk.CTkLabel(
                tier, text=f"{baht:,} Baht",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="#2563eb" if ctk.get_appearance_mode() == "Light" else "#60a5fa",
            ).pack(anchor="w", padx=12, pady=(0, 8))
        rows_used = (len(PRICING_TIERS) + 1) // 2
        over = ctk.CTkFrame(price_card, corner_radius=10, fg_color=("gray90", "gray20"))
        over.grid(row=rows_used + 1, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 12))
        over.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(over, text=PRICING_OVER_YEAR_TEXT, anchor="w").grid(
            row=0, column=0, sticky="w", padx=12, pady=10
        )
        ctk.CTkButton(
            over, text="WhatsApp us", width=130, height=30,
            fg_color="#128C7E", hover_color="#075E54",
            command=lambda: open_whatsapp_chat(
                "SkyAdmin Pro — I'm interested in a license over 1 year.\n"
                f"Machine ID: {machine_id}"
            ),
        ).grid(row=0, column=1, sticky="e", padx=12, pady=6)

        ctk.CTkLabel(
            price_card,
            text=(
                "Payment: contact us on WhatsApp or email —\n"
                f"{OWNER_WHATSAPP_DISPLAY} · {OWNER_EMAIL}\n"
                "After payment you receive a one-time activation code."
            ),
            justify="center",
            text_color=TEXT_MUTED,
        ).grid(row=rows_used + 2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 12))

        # ---- Machine ID card ----
        mid_card = ctk.CTkFrame(body, corner_radius=CARD_RADIUS)
        mid_card.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))
        mid_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(mid_card, text="Your Machine ID", anchor="w", text_color=TEXT_MUTED).grid(
            row=0, column=0, sticky="w", padx=16, pady=(12, 2)
        )
        ctk.CTkLabel(
            mid_card, text=machine_id,
            font=ctk.CTkFont(size=19, weight="bold"), anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=16)
        ctk.CTkButton(
            mid_card, text="Copy Machine ID", width=160,
            fg_color="transparent", border_width=1, command=self._copy_mid,
        ).grid(row=2, column=0, sticky="w", padx=16, pady=(6, 12))

        # ---- Step 1: email request ----
        ctk.CTkLabel(
            body, text="1. Enter your email — we reply with your code:",
            anchor="w",
        ).grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 4))
        self.email_var = ctk.StringVar()
        ctk.CTkEntry(
            body, textvariable=self.email_var,
            placeholder_text="yourname@gmail.com",
        ).grid(row=5, column=0, sticky="ew", padx=16)
        req_row = ctk.CTkFrame(body, fg_color="transparent")
        req_row.grid(row=6, column=0, sticky="ew", padx=16, pady=(8, 0))
        req_row.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(
            req_row, text="Request Code by Email", height=38, command=self._request_email
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            req_row, text="Discuss on WhatsApp", height=38,
            fg_color="#128C7E", hover_color="#075E54",
            command=lambda: open_whatsapp_chat(activation_request_message(self._customer_email())),
        ).grid(row=1, column=0, sticky="ew", pady=(6, 0))
        ctk.CTkLabel(
            req_row,
            text=f"Email: {OWNER_EMAIL}   ·   WhatsApp: {OWNER_WHATSAPP_DISPLAY}",
            text_color=TEXT_MUTED, anchor="w", wraplength=500, justify="left",
        ).grid(row=2, column=0, sticky="ew", pady=(8, 0))

        # ---- Step 2: paste code ----
        ctk.CTkLabel(
            body,
            text="2. Paste the License Key or 8-digit Passcode you received:",
            anchor="w",
        ).grid(row=7, column=0, sticky="ew", padx=16, pady=(14, 4))
        self.key_box = ctk.CTkTextbox(body, height=80, wrap="char")
        self.key_box.grid(row=8, column=0, sticky="ew", padx=16)

        self.status = ctk.CTkLabel(
            body, text="", anchor="w", justify="left", wraplength=520,
        )
        self.status.grid(row=9, column=0, sticky="ew", padx=16, pady=(8, 0))

        # ---- Actions ----
        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.grid(row=10, column=0, sticky="ew", padx=16, pady=(10, 20))
        actions.grid_columnconfigure(0, weight=1)
        self.activate_btn = ctk.CTkButton(
            actions, text="Activate Now", height=42, command=self._activate
        )
        self.activate_btn.grid(row=0, column=0, sticky="ew")
        bottom = ctk.CTkFrame(actions, fg_color="transparent")
        bottom.grid(row=1, column=0, sticky="ew", pady=(8, 14))
        self.continue_btn = ctk.CTkButton(
            bottom, text="Continue to App", height=34,
            state="disabled", command=self._continue,
        )
        self.continue_btn.pack(side="left")
        ctk.CTkButton(
            bottom, text="License", height=34,
            fg_color="transparent", border_width=1, command=self._show_license_text,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            bottom, text="Disclaimer", height=34,
            fg_color="transparent", border_width=1, command=self._show_disclaimer_text,
        ).pack(side="left", padx=(6, 0))
        if allow_quit:
            ctk.CTkButton(
                bottom, text="Quit", height=34, fg_color="transparent",
                border_width=1, command=self._quit,
            ).pack(side="right")

        self.bind("<Escape>", lambda _e: self._close())
        self.protocol("WM_DELETE_WINDOW", self._close)

    # ------------------------------------------------------------------ #
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
            except Exception:
                pass
        self._set_status("Machine ID copied.", "info")

    def _request_email(self) -> None:
        email = self._customer_email()
        if not email or "@" not in email or "." not in email.split("@")[-1]:
            self._set_status("Enter a valid email first — the code is replied there.", "error")
            return
        subject = "SkyAdmin Pro — License Request"
        body = activation_request_message(email)
        url = (
            f"mailto:{OWNER_EMAIL}?subject={quote(subject)}"
            f"&body={quote(body)}"
        )
        _open_url(url)
        try:
            import pyperclip

            pyperclip.copy(body)
        except Exception:
            pass
        self._set_status(
            "Email opened — press Send. We reply to your email with the code,"
            " then paste it below. (Request also copied to clipboard.)",
            "info",
        )

    def _activate(self) -> None:
        if getattr(self, "_activating", False):
            return
        content = "".join(self.key_box.get("1.0", "end").split())
        # One-time-use gate: signature/machine/expiry + burn-list check
        ok, msg, nonce = check_activation_usable(content)
        if not ok:
            self._set_status(f"✗ {msg}", "error")
            return

        from skyadmin_pro.config import REVOCATION_URL

        needs_online = bool(REVOCATION_URL.strip())
        self._activating = True
        self.activate_btn.configure(state="disabled", text="Checking…")

        def _finish(ok_final: bool, message: str, nonce_final: str | None) -> None:
            self._activating = False
            self.activate_btn.configure(state="normal", text="Activate Now")
            if not ok_final:
                self._set_status(f"✗ {message}", "error")
                return
            save_license_file(content)
            # Burn the code: it can never be redeemed again on any machine.
            if nonce_final:
                mark_used(nonce_final)
            self._set_status(f"✓ {message} Activation complete.", "success")
            self.continue_btn.configure(state="normal")
            if self._on_activated is not None:
                try:
                    self._on_activated()
                except Exception:
                    pass

        if not needs_online:
            _finish(True, msg, nonce)
            return

        # Online activation: refresh the owner's control list in a worker so
        # a slow connection never freezes the dialog (6s timeout max).
        self._set_status("Checking license online…", "info")

        def worker():
            net_ok, net_msg = fetch_revocations()
            if not net_ok:
                result_ok, result_msg, result_nonce = False, (
                    "Internet connection is required to activate. "
                    "Please connect and try again."
                ), None
            else:
                # Re-run the FULL gate AFTER syncing revocations/bans/used —
                # remotely revoked, banned or already-used codes must be
                # rejected here.
                ok2, msg2, n2 = check_activation_usable(content)
                result_ok, result_msg, result_nonce = ok2, msg2, n2

            def done():
                if not self.winfo_exists():
                    return
                _finish(result_ok, result_msg, result_nonce)

            try:
                self.after(0, done)
            except Exception:
                pass

        import threading

        threading.Thread(target=worker, daemon=True).start()

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
        except Exception:
            pass
        top.bind("<Escape>", lambda _e: top.destroy())
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(0, weight=1)
        box = ctk.CTkTextbox(top, wrap="word")
        box.grid(row=0, column=0, sticky="nsew", padx=14, pady=(14, 6))
        box.insert("1.0", text)
        box.configure(state="disabled")
        ctk.CTkButton(top, text="Close", width=110, command=top.destroy).grid(
            row=1, column=0, pady=(0, 14)
        )

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
                except Exception:
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

    result = {"done": False}
    root = tk.Tk()
    root.withdraw()

    def _finish() -> None:
        result["done"] = True
        root.quit()

    dialog = ActivationDialog(None, allow_quit=True, on_close_request=_finish)
    root.mainloop()
    try:
        dialog.destroy()
    except Exception:
        pass
    root.destroy()
    ok, _msg = verify_license()
    return ok