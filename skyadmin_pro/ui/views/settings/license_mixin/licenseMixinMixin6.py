from __future__ import annotations

from skyadmin_pro.ui.theme import FEEDBACK_SUCCESS, TEXT_MUTED


class LicenseMixinMixin6:
    def _refresh_mobile_vault_status(self) -> None:
        from skyadmin_pro.services.mobile_vault import mobile_vault_configured

        label = getattr(self, "mobile_vault_status", None)
        if label is None:
            return
        if mobile_vault_configured(self.app.db):
            label.configure(text="Passphrase set (local). Sync Now pushes ciphertext.", text_color=FEEDBACK_SUCCESS)
        else:
            label.configure(
                text="Not set — Sync skips password columns (metadata still syncs).",
                text_color=TEXT_MUTED,
            )

    def _save_mobile_vault(self) -> None:
        from skyadmin_pro.services.mobile_vault import set_mobile_vault_passphrase

        entry = getattr(self, "mobile_vault_entry", None)
        phrase = (entry.get() if entry is not None else "") or ""
        ok, msg = set_mobile_vault_passphrase(self.app.db, phrase)
        if ok:
            if entry is not None:
                entry.delete(0, "end")
            self.feedback.success(msg.splitlines()[0])
        else:
            self.feedback.error(msg)
        self._refresh_mobile_vault_status()

    def _clear_mobile_vault(self) -> None:
        from skyadmin_pro.services.mobile_vault import clear_mobile_vault

        clear_mobile_vault(self.app.db)
        entry = getattr(self, "mobile_vault_entry", None)
        if entry is not None:
            entry.delete(0, "end")
        self.feedback.info("Mobile Vault passphrase cleared — Sync will skip password columns.")
        self._refresh_mobile_vault_status()
