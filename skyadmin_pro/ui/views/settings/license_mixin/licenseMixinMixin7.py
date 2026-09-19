from __future__ import annotations


class LicenseMixinMixin7:
    def _format_data_sync_status(self) -> str:
        from skyadmin_pro.config import SETTING_DATA_SYNC_ENABLED, SETTING_SYNC_LAST_PULL
        from skyadmin_pro.services.data_sync import is_data_sync_enabled
        from skyadmin_pro.services.drive.entitlement import (
            license_allows_sync,
            license_allows_web,
            license_devices_status_fragment,
        )

        web = "Web access: included" if license_allows_web(self.app.db) else "Web access: not on this license"
        devices = license_devices_status_fragment(self.app.db)
        tail = f"{web}" + (f" · {devices}" if devices else "")
        if not license_allows_sync(self.app.db):
            return f"Cloud data sync: locked (license SKU) · {tail}"
        if (self.app.db.get_setting(SETTING_DATA_SYNC_ENABLED) or "0").strip() != "1":
            return f"Cloud data sync: off (use encrypted backup for a second PC) · {tail}"
        if not is_data_sync_enabled(self.app.db):
            return f"Cloud data sync: off · {tail}"
        last = (self.app.db.get_setting(SETTING_SYNC_LAST_PULL) or "").strip()
        conflicts = self.app.db.count_sync_conflicts()
        parts: list[str] = []
        if last:
            parts.append(f"Last data sync: {last.replace('T', ' ')[:19]}")
        else:
            parts.append("Data sync: never")
        if conflicts:
            parts.append(f"{conflicts} sync conflict(s) logged")
        parts.append(web)
        if devices:
            parts.append(devices)
        return " · ".join(parts)

    def _apply_data_sync_status_ui(self) -> None:
        from skyadmin_pro.config import SETTING_DATA_SYNC_ENABLED, SETTING_SYNC_AUTO_INTERVAL
        from skyadmin_pro.services.data_sync import normalize_sync_auto_interval
        from skyadmin_pro.services.drive.entitlement import license_allows_sync

        self.data_sync_label.configure(text=self._format_data_sync_status())
        allowed = license_allows_sync(self.app.db)
        pref_on = (self.app.db.get_setting(SETTING_DATA_SYNC_ENABLED) or "0").strip() == "1"
        if getattr(self, "data_sync_var", None) is not None:
            self.data_sync_var.set(bool(allowed and pref_on))
        cb = getattr(self, "_data_sync_cb", None)
        if cb is not None:
            cb.configure(state="normal" if allowed else "disabled")
        menu = getattr(self, "_sync_auto_menu", None)
        if menu is not None:
            menu.configure(state="normal" if allowed else "disabled")
        if getattr(self, "_sync_auto_interval_var", None) is not None:
            self._sync_auto_interval_var.set(
                normalize_sync_auto_interval(self.app.db.get_setting(SETTING_SYNC_AUTO_INTERVAL))
            )

    def _on_data_sync_toggle(self) -> None:
        from skyadmin_pro.config import SETTING_DATA_SYNC_ENABLED
        from skyadmin_pro.services.drive.entitlement import license_allows_sync

        if not license_allows_sync(self.app.db):
            self.data_sync_var.set(False)
            self.app.db.set_setting(SETTING_DATA_SYNC_ENABLED, "0")
            self._nudge_auto_sync()
            self._refresh_license_label()
            self.feedback.error("Cloud sync is not enabled on this license.")
            return
        enabled = bool(self.data_sync_var.get())
        self.app.db.set_setting(SETTING_DATA_SYNC_ENABLED, "1" if enabled else "0")
        self._nudge_auto_sync()
        self._refresh_license_label()
        if enabled:
            self.feedback.info("Cloud data sync enabled for this licensed PC only.")
        else:
            self.feedback.info("Cloud data sync disabled — use encrypted backup for a second PC.")
