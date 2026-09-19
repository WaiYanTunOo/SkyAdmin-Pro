from __future__ import annotations

from skyadmin_pro.ui.theme import TEXT_MUTED


class LicenseMixinMixin4:
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
                self._apply_data_sync_status_ui()
                count = self.app.db.count_sync_conflicts()
                self.conflicts_btn.configure(
                    state="normal" if count else "disabled",
                    text=f"Conflicts ({count})" if count else "Conflicts",
                )
            except Exception:
                self.daily_sync_label.configure(text="")
                try:
                    self.data_sync_label.configure(text="")
                except Exception as e:
                    import logging

                    logging.error(f"UI Error: {e}")
        except Exception:
            self.license_label.configure(text="License: unavailable")
            try:
                self.daily_sync_label.configure(text="")
                self.data_sync_label.configure(text="")
            except Exception as e:
                import logging

                logging.error(f"UI Error: {e}")

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
