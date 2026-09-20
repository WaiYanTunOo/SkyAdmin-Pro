from __future__ import annotations


class LicenseMixinMixin2:
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
                claim_ok, claim_msg, license_key, claim_data = report_activation_claim(
                    content,
                    allow_already_claimed=_is_repair_activation(content),
                )
                if not claim_ok:
                    return False, claim_msg
                if claim_data and any(
                    k in claim_data
                    for k in ("sync_enabled", "web_enabled", "drive_files_enabled", "max_devices", "org_id")
                ):
                    from skyadmin_pro.services.data_sync.entitlements import apply_sku_flags_from_response

                    apply_sku_flags_from_response(self.app.db, claim_data)
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
