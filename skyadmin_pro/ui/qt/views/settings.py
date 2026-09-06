"""Qt Settings port (Phase 3 follow-up).

Mirrors ``ui/views/settings/view.py`` sections — License, Sync, Backup,
Pricing, Appearance — as a QTabWidget page. Builds offscreen-safe (no
modal popups on the build path); long work goes through the async bridge
with status-label feedback.
"""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

TAB_TITLES = ("License", "Sync", "Backup", "Pricing", "Appearance")

PRICING_COLUMNS = (
    ("range", "Range / charge"),
    ("monthly", "Monthly THB"),
    ("annual", "Annual THB"),
    ("sla", "SLA hrs"),
    ("headcount", "HC"),
    ("docs", "Required docs"),
)

CONFLICT_COLUMNS = (
    ("logged_at", "Logged"),
    ("table_name", "Table"),
    ("global_id", "Global ID"),
    ("direction", "Dir"),
    ("local_updated_at", "Local updated"),
    ("remote_updated_at", "Remote updated"),
)


def license_status_text() -> str:
    try:
        from skyadmin_pro.services.license import license_status_text as _status

        return str(_status())
    except Exception:
        return "License: unavailable"


def machine_id_text() -> str:
    try:
        from skyadmin_pro.services.license import get_machine_id

        return str(get_machine_id())
    except Exception:
        return "unknown"


def build_page(db, paths=None):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QScrollArea,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )

    from skyadmin_pro.ui.qt import async_bridge, theme_bridge
    from skyadmin_pro.ui.qt.widgets import make_table, set_table_rows

    page = QWidget()
    page.db = db
    page.paths = paths
    page._appearance_mode = ""
    outer = QVBoxLayout(page)

    title = QLabel("Settings")
    title.setObjectName("qt-shell-title")
    outer.addWidget(title)
    subtitle = QLabel("License, sync, backup, pricing, and appearance.")
    subtitle.setObjectName("qt-shell-subtitle")
    subtitle.setWordWrap(True)
    outer.addWidget(subtitle)

    tabs = QTabWidget()
    tabs.setObjectName("qt-settings-tabs")
    outer.addWidget(tabs, 1)

    status = QLabel("")
    status.setObjectName("qt-settings-status")
    status.setWordWrap(True)
    outer.addWidget(status)

    def set_status(message: str) -> None:
        status.setText(str(message))

    page.set_status = set_status  # type: ignore[attr-defined]

    def _scroll_wrap() -> tuple[QWidget, QVBoxLayout]:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        scroll.setWidget(body)
        return scroll, layout

    def _section(layout: QVBoxLayout, heading: str, blurb: str = "") -> QVBoxLayout:
        head = QLabel(heading)
        head.setObjectName("qt-shell-title")
        layout.addWidget(head)
        if blurb:
            sub = QLabel(blurb)
            sub.setObjectName("qt-shell-subtitle")
            sub.setWordWrap(True)
            layout.addWidget(sub)
        box = QVBoxLayout()
        layout.addLayout(box)
        return box

    # -- License tab ----------------------------------------------------
    license_scroll, license_layout = _scroll_wrap()
    license_box = _section(
        license_layout,
        "License",
        "License status for this PC. Activation never crashes — failures show inline.",
    )
    license_status = QLabel(license_status_text())
    license_status.setObjectName("qt-settings-license-status")
    license_status.setWordWrap(True)
    license_box.addWidget(license_status)
    machine_label = QLabel(f"Machine ID: {machine_id_text()}")
    machine_label.setObjectName("qt-settings-machine-id")
    machine_label.setWordWrap(True)
    machine_label.setTextInteractionFlags(
        machine_label.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse
    )
    license_box.addWidget(machine_label)
    activate_button = QPushButton("Activate / Manage License…")
    activate_button.setObjectName("qt-settings-activate")
    license_box.addWidget(activate_button)
    license_layout.addStretch(1)
    tabs.addTab(license_scroll, "License")
    page.license_status_label = license_status  # type: ignore[attr-defined]
    page.machine_label = machine_label  # type: ignore[attr-defined]
    page.activate_button = activate_button  # type: ignore[attr-defined]

    def refresh_license() -> None:
        license_status.setText(license_status_text())
        machine_label.setText(f"Machine ID: {machine_id_text()}")

    page.refresh_license = refresh_license  # type: ignore[attr-defined]

    def verify_activation_code(code: str) -> tuple[bool, str]:
        from skyadmin_pro.services.license import (
            check_activation_usable,
            mark_used,
            save_license_file,
        )

        text = (code or "").strip()
        if not text:
            return False, "Paste a license key or passcode first."
        try:
            ok, msg, nonce = check_activation_usable(text)
        except Exception as exc:
            log.warning("Qt activation verify failed: %s", exc)
            return False, str(exc).splitlines()[0] if str(exc) else "Activation failed."
        if not ok:
            return False, (msg or "Activation failed.").splitlines()[0]
        try:
            save_license_file(text)
        except Exception as exc:
            return False, f"Could not save license: {exc}".splitlines()[0]
        if nonce:
            try:
                mark_used(nonce)
            except Exception:
                log.warning("Qt activation mark_used failed", exc_info=True)
        return True, (msg or "Activated.").splitlines()[0]

    page.verify_activation_code = verify_activation_code  # type: ignore[attr-defined]

    def open_activation_dialog():
        try:
            import skyadmin_pro.config as _config

            owner_contact = str(getattr(_config, "OWNER_EMAIL", "") or "")
        except Exception:
            owner_contact = ""
        dialog = QDialog(page)
        dialog.setObjectName("qt-settings-activate-dialog")
        dialog.setWindowTitle("SkyAdmin Pro — Activate License")
        dialog.setMinimumWidth(420)
        box = QVBoxLayout(dialog)
        info = QLabel(
            f"Paste a full license key, or a SKYPASS1 passcode from your administrator. Questions: {owner_contact}"
            if owner_contact
            else "Paste a full license key, or a SKYPASS1 passcode."
        )
        info.setWordWrap(True)
        box.addWidget(info)
        form = QFormLayout()
        email_edit = QLineEdit()
        email_edit.setObjectName("qt-settings-activate-email")
        email_edit.setPlaceholderText("you@example.com")
        form.addRow("Email", email_edit)
        code_edit = QLineEdit()
        code_edit.setObjectName("qt-settings-activate-code")
        code_edit.setPlaceholderText("Paste license key or SKYPASS1:…")
        form.addRow("Code", code_edit)
        box.addLayout(form)
        error_label = QLabel("")
        error_label.setObjectName("qt-settings-activate-error")
        error_label.setWordWrap(True)
        box.addWidget(error_label)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        verify_button = QPushButton("Activate")
        verify_button.setObjectName("qt-settings-activate-verify")
        buttons.addButton(verify_button, QDialogButtonBox.ButtonRole.AcceptRole)
        box.addWidget(buttons)
        buttons.rejected.connect(dialog.reject)

        def _on_verify() -> None:
            code_text = code_edit.text()
            verify_button.setEnabled(False)
            error_label.setText("Verifying…")

            def work():
                return verify_activation_code(code_text)

            def on_success(result) -> None:
                verify_button.setEnabled(True)
                try:
                    ok, msg = result
                except Exception:
                    error_label.setText("Activation failed.")
                    return
                if ok:
                    refresh_license()
                    set_status(f"License activated: {msg}")
                    dialog.accept()
                else:
                    error_label.setText(str(msg))

            def on_error(message: str) -> None:
                verify_button.setEnabled(True)
                error_label.setText(str(message).splitlines()[0])

            async_bridge.run_background_q(page, work=work, on_success=on_success, on_error=on_error)

        verify_button.clicked.connect(_on_verify)
        dialog.show()
        return dialog

    page.open_activation_dialog = open_activation_dialog  # type: ignore[attr-defined]
    activate_button.clicked.connect(open_activation_dialog)

    # -- Sync tab -------------------------------------------------------
    sync_scroll, sync_layout = _scroll_wrap()
    sync_box = _section(
        sync_layout,
        "Sync",
        "Optional cloud sync for this licensed PC only. Conflicts are audit-only (local data kept).",
    )
    try:
        from skyadmin_pro.config import SETTING_DATA_SYNC_ENABLED

        _sync_enabled = (db.get_setting(SETTING_DATA_SYNC_ENABLED) or "0").strip() == "1"
    except Exception:
        _sync_enabled = False
    sync_toggle = QCheckBox("Enable cloud data sync (this licensed PC only)")
    sync_toggle.setObjectName("qt-settings-sync-enabled")
    sync_toggle.setChecked(bool(_sync_enabled))
    sync_box.addWidget(sync_toggle)
    last_pull_label = QLabel("")
    last_pull_label.setObjectName("qt-settings-last-pull")
    last_pull_label.setWordWrap(True)
    sync_box.addWidget(last_pull_label)
    last_push_label = QLabel("")
    last_push_label.setObjectName("qt-settings-last-push")
    last_push_label.setWordWrap(True)
    sync_box.addWidget(last_push_label)
    sync_row = QHBoxLayout()
    sync_now_button = QPushButton("Sync Now")
    sync_now_button.setObjectName("qt-settings-sync-now")
    sync_row.addWidget(sync_now_button)
    conflicts_button = QPushButton("Conflicts")
    conflicts_button.setObjectName("qt-settings-conflicts")
    sync_row.addWidget(conflicts_button)
    clear_log_button = QPushButton("Clear log")
    clear_log_button.setObjectName("qt-settings-clear-log")
    sync_row.addWidget(clear_log_button)
    sync_row.addStretch(1)
    sync_box.addLayout(sync_row)
    sync_status = QLabel("")
    sync_status.setObjectName("qt-settings-sync-status")
    sync_status.setWordWrap(True)
    sync_box.addWidget(sync_status)
    sync_layout.addStretch(1)
    tabs.addTab(sync_scroll, "Sync")
    page.sync_toggle = sync_toggle  # type: ignore[attr-defined]
    page.sync_now_button = sync_now_button  # type: ignore[attr-defined]
    page.last_pull_label = last_pull_label  # type: ignore[attr-defined]
    page.last_push_label = last_push_label  # type: ignore[attr-defined]
    page.conflicts_button = conflicts_button  # type: ignore[attr-defined]
    page.clear_log_button = clear_log_button  # type: ignore[attr-defined]
    page.sync_status_label = sync_status  # type: ignore[attr-defined]

    def refresh_sync() -> None:
        try:
            from skyadmin_pro.config import (
                SETTING_DATA_SYNC_ENABLED,
                SETTING_SYNC_LAST_PULL,
                SETTING_SYNC_LAST_PUSH,
            )

            enabled = (db.get_setting(SETTING_DATA_SYNC_ENABLED) or "0").strip() == "1"
            sync_toggle.blockSignals(True)
            try:
                sync_toggle.setChecked(enabled)
            finally:
                sync_toggle.blockSignals(False)
            last_pull = (db.get_setting(SETTING_SYNC_LAST_PULL) or "").strip()
            last_push = (db.get_setting(SETTING_SYNC_LAST_PUSH) or "").strip()
            last_pull_label.setText(
                f"Last pull: {last_pull.replace('T', ' ')[:19]}" if last_pull else "Last pull: never"
            )
            last_push_label.setText(
                f"Last push: {last_push.replace('T', ' ')[:19]}" if last_push else "Last push: never"
            )
        except Exception:
            log.warning("Qt settings sync refresh failed", exc_info=True)
        try:
            count = int(db.count_sync_conflicts())
        except Exception:
            count = 0
        conflicts_button.setText(f"Conflicts ({count})" if count else "Conflicts")
        clear_log_button.setEnabled(count > 0)

    page.refresh_sync = refresh_sync  # type: ignore[attr-defined]

    def _on_sync_toggle(checked: bool) -> None:
        try:
            from skyadmin_pro.config import SETTING_DATA_SYNC_ENABLED

            db.set_setting(SETTING_DATA_SYNC_ENABLED, "1" if checked else "0")
            sync_status.setText(
                "Cloud data sync enabled for this licensed PC only."
                if checked
                else "Cloud data sync disabled — use encrypted backup for a second PC."
            )
        except Exception as exc:
            sync_status.setText(f"Could not save sync setting: {exc}")
        refresh_sync()

    sync_toggle.toggled.connect(_on_sync_toggle)

    def sync_once() -> tuple[bool, str]:
        from skyadmin_pro.services.data_sync import sync_data

        try:
            return sync_data(db, timeout=25)
        except Exception as exc:
            log.warning("Qt sync failed: %s", exc)
            return False, str(exc).splitlines()[0] if str(exc) else "Sync failed."

    page.sync_once = sync_once  # type: ignore[attr-defined]

    def _on_sync_now() -> None:
        sync_now_button.setEnabled(False)
        sync_status.setText("Syncing…")

        def on_success(result) -> None:
            sync_now_button.setEnabled(True)
            try:
                ok, msg = result
            except Exception:
                sync_status.setText("Sync finished.")
                refresh_sync()
                return
            sync_status.setText(str(msg).splitlines()[0])
            set_status(str(msg).splitlines()[0])
            refresh_sync()

        def on_error(message: str) -> None:
            sync_now_button.setEnabled(True)
            sync_status.setText(str(message).splitlines()[0])
            refresh_sync()

        async_bridge.run_background_q(page, work=sync_once, on_success=on_success, on_error=on_error)

    sync_now_button.clicked.connect(_on_sync_now)

    def open_conflicts_dialog():
        dialog = QDialog(page)
        dialog.setObjectName("qt-settings-conflicts-dialog")
        dialog.setWindowTitle("SkyAdmin Pro — Sync conflicts")
        dialog.resize(760, 480)
        box = QVBoxLayout(dialog)
        try:
            total = int(db.count_sync_conflicts())
        except Exception:
            total = 0
        if total <= 0:
            summary = QLabel("No sync conflicts logged. Local data is always kept on conflict.")
        else:
            summary = QLabel(f"{total} conflict(s) logged — your local data was kept (audit only).")
        summary.setObjectName("qt-settings-conflicts-summary")
        summary.setWordWrap(True)
        box.addWidget(summary)
        table = make_table(dialog)
        table.setObjectName("qt-settings-conflicts-table")
        box.addWidget(table, 1)
        try:
            rows = db.list_sync_conflicts(limit=500)
        except Exception as exc:
            rows = []
            summary.setText(f"Could not load conflicts: {exc}")
        clipped = [
            {
                k: (str(v)[:19] if k in ("logged_at", "local_updated_at", "remote_updated_at") and v else v)
                for k, v in row.items()
            }
            for row in rows
        ]
        set_table_rows(table, CONFLICT_COLUMNS, clipped)
        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        close_row.addWidget(close_button)
        box.addLayout(close_row)
        dialog.show()
        return dialog

    page.open_conflicts_dialog = open_conflicts_dialog  # type: ignore[attr-defined]
    conflicts_button.clicked.connect(open_conflicts_dialog)

    def _on_clear_log() -> None:
        try:
            cleared = int(db.clear_sync_conflicts())
        except Exception as exc:
            sync_status.setText(f"Could not clear conflict log: {exc}")
            return
        sync_status.setText(f"Cleared {cleared} sync conflict log entries (data unchanged).")
        set_status(f"Cleared {cleared} sync conflict(s).")
        refresh_sync()

    clear_log_button.clicked.connect(_on_clear_log)

    # -- Backup tab -----------------------------------------------------
    backup_scroll, backup_layout = _scroll_wrap()
    backup_box = _section(
        backup_layout,
        "Backup",
        "Encrypted .skybackup files move data to another PC. Restore always previews first.",
    )
    backup_banner = QLabel("")
    backup_banner.setObjectName("qt-settings-backup-banner")
    backup_banner.setWordWrap(True)
    backup_box.addWidget(backup_banner)
    backup_row = QHBoxLayout()
    backup_button = QPushButton("Create encrypted backup…")
    backup_button.setObjectName("qt-settings-backup-create")
    backup_row.addWidget(backup_button)
    restore_button = QPushButton("Restore with preview…")
    restore_button.setObjectName("qt-settings-backup-restore")
    backup_row.addWidget(restore_button)
    integrity_button = QPushButton("Check integrity")
    integrity_button.setObjectName("qt-settings-integrity")
    backup_row.addWidget(integrity_button)
    backup_row.addStretch(1)
    backup_box.addLayout(backup_row)
    integrity_result = QLabel("")
    integrity_result.setObjectName("qt-settings-integrity-result")
    integrity_result.setWordWrap(True)
    backup_box.addWidget(integrity_result)
    backup_status = QLabel("")
    backup_status.setObjectName("qt-settings-backup-status")
    backup_status.setWordWrap(True)
    backup_box.addWidget(backup_status)
    backup_layout.addStretch(1)
    tabs.addTab(backup_scroll, "Backup")
    page.backup_button = backup_button  # type: ignore[attr-defined]
    page.restore_button = restore_button  # type: ignore[attr-defined]
    page.integrity_button = integrity_button  # type: ignore[attr-defined]
    page.integrity_result_label = integrity_result  # type: ignore[attr-defined]
    page.backup_status_label = backup_status  # type: ignore[attr-defined]
    page.backup_banner_label = backup_banner  # type: ignore[attr-defined]

    def refresh_backup_banner() -> None:
        try:
            from datetime import date as _date

            from skyadmin_pro.config import SETTING_LAST_ENCRYPTED_BACKUP

            raw = (db.get_setting(SETTING_LAST_ENCRYPTED_BACKUP) or "").strip()
        except Exception:
            backup_banner.setText("")
            return
        if not raw:
            backup_banner.setText("You have NEVER created an encrypted backup — create one now.")
            return
        try:
            last = _date.fromisoformat(raw[:10])
            days = (_date.today() - last).days
        except ValueError:
            backup_banner.setText("Last backup date is unreadable — create a fresh backup.")
            return
        if days >= 7:
            backup_banner.setText(f"Last encrypted backup was {days} day(s) ago — create a fresh one.")
        else:
            backup_banner.setText(f"Last encrypted backup: {last.isoformat()} ({days} day(s) ago).")

    page.refresh_backup_banner = refresh_backup_banner  # type: ignore[attr-defined]

    def backup_to(dest: str | Path) -> Path | None:
        from skyadmin_pro.services.crypto import create_encrypted_backup, format_byte_size

        if paths is None or getattr(paths, "root", None) is None:
            backup_status.setText("Workspace paths are unavailable — backup aborted.")
            return None
        dest_path = Path(dest)
        created = create_encrypted_backup(Path(paths.root), Path(db.db_file), dest_path)
        size = format_byte_size(created.stat().st_size)
        try:
            from datetime import date as _date

            from skyadmin_pro.config import SETTING_LAST_ENCRYPTED_BACKUP

            db.set_setting(SETTING_LAST_ENCRYPTED_BACKUP, _date.today().isoformat())
        except Exception:
            log.warning("Qt settings backup stamp failed", exc_info=True)
        refresh_backup_banner()
        backup_status.setText(f"Encrypted backup saved: {created.name} ({size})")
        set_status(f"Backup saved to {created}")
        return created

    page.backup_to = backup_to  # type: ignore[attr-defined]

    def _on_backup_create() -> None:
        from datetime import date as _date

        suggested = f"SkyAdminPro_Backup_{_date.today().isoformat()}.skybackup"
        dest, _ = QFileDialog.getSaveFileName(page, "Save Encrypted Backup", suggested, "SkyAdmin Backup (*.skybackup)")
        if not dest:
            return
        backup_button.setEnabled(False)
        backup_status.setText("Creating encrypted backup…")

        def on_success(saved) -> None:
            backup_button.setEnabled(True)
            if saved is None:
                return

        def on_error(message: str) -> None:
            backup_button.setEnabled(True)
            backup_status.setText(f"Backup failed: {str(message).splitlines()[0]}")

        async_bridge.run_background_q(page, work=lambda: backup_to(dest), on_success=on_success, on_error=on_error)

    backup_button.clicked.connect(_on_backup_create)

    def check_integrity() -> bool:
        try:
            ok = bool(db.quick_check())
        except Exception as exc:
            log.warning("Qt integrity check failed: %s", exc)
            ok = False
        if ok:
            integrity_result.setText("quick_check passed — your local database looks healthy.")
        else:
            integrity_result.setText("Integrity check failed — restore from an encrypted backup.")
        return ok

    page.check_integrity = check_integrity  # type: ignore[attr-defined]

    def _on_integrity() -> None:
        integrity_button.setEnabled(False)
        integrity_result.setText("Checking database integrity…")

        def on_success(ok) -> None:
            integrity_button.setEnabled(True)
            set_status("Database integrity check passed." if ok else "Database integrity check failed.")

        def on_error(message: str) -> None:
            integrity_button.setEnabled(True)
            integrity_result.setText(f"Integrity check could not run: {str(message).splitlines()[0]}")

        async_bridge.run_background_q(page, work=check_integrity, on_success=on_success, on_error=on_error)

    integrity_button.clicked.connect(_on_integrity)

    def inspect_backup(archive: str | Path):
        from skyadmin_pro.services.crypto import inspect_encrypted_backup

        return inspect_encrypted_backup(Path(archive))

    page.inspect_backup = inspect_backup  # type: ignore[attr-defined]

    def restore_from(archive: str | Path):
        from datetime import datetime as _dt

        from skyadmin_pro.services.crypto import create_encrypted_backup, restore_encrypted_backup

        if paths is None or getattr(paths, "root", None) is None:
            raise RuntimeError("Workspace paths are unavailable — restore aborted.")
        src = Path(archive)
        try:
            db.shutdown()
        except Exception:
            pass
        backup_dir = Path(db.db_file).parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = _dt.now().strftime("%Y%m%d_%H%M%S")
        safety_path = backup_dir / f"pre_restore_{stamp}.skybackup"
        create_encrypted_backup(Path(paths.root), Path(db.db_file), safety_path)
        return restore_encrypted_backup(src, Path(paths.root), Path(db.db_file))

    page.restore_from = restore_from  # type: ignore[attr-defined]

    def _on_restore() -> None:
        chosen, _ = QFileDialog.getOpenFileName(page, "Restore Encrypted Backup", "", "SkyAdmin Backup (*.skybackup)")
        if not chosen:
            return
        backup_status.setText("Reading backup…")

        def work():
            return inspect_backup(chosen)

        def on_success(info) -> None:
            from skyadmin_pro.services.crypto import format_byte_size

            if not info.has_database:
                backup_status.setText("Invalid backup: no database inside — restore aborted.")
                return
            preview = QDialog(page)
            preview.setObjectName("qt-settings-restore-preview")
            preview.setWindowTitle("Restore backup — preview")
            preview.setMinimumWidth(440)
            box = QVBoxLayout(preview)
            detail = QLabel(
                f"Backup file: {Path(chosen).name}\n"
                f"Encrypted size: {format_byte_size(info.encrypted_bytes)}\n"
                f"Database: {format_byte_size(info.database_bytes)}\n"
                f"Workspace: {info.workspace_file_count} file(s), "
                f"{format_byte_size(info.workspace_bytes)}\n\n"
                "Current data will be overwritten (a safety copy is saved first)."
            )
            detail.setWordWrap(True)
            box.addWidget(detail)
            row = QHBoxLayout()
            row.addStretch(1)
            cancel_button = QPushButton("Cancel")
            cancel_button.clicked.connect(preview.reject)
            row.addWidget(cancel_button)
            confirm_button = QPushButton("Restore")
            confirm_button.setObjectName("qt-settings-restore-confirm")
            row.addWidget(confirm_button)
            box.addLayout(row)

            def _on_confirm() -> None:
                preview.accept()
                backup_status.setText("Restoring encrypted backup…")
                restore_button.setEnabled(False)

                def on_restored(_summary) -> None:
                    restore_button.setEnabled(True)
                    backup_status.setText("Restore complete — please restart the app.")
                    set_status("Restore complete — restart required")

                def on_restore_error(message: str) -> None:
                    restore_button.setEnabled(True)
                    backup_status.setText(f"Restore failed: {str(message).splitlines()[0]}")

                async_bridge.run_background_q(
                    page,
                    work=lambda: restore_from(chosen),
                    on_success=on_restored,
                    on_error=on_restore_error,
                )

            confirm_button.clicked.connect(_on_confirm)
            preview.show()

        def on_error(message: str) -> None:
            backup_status.setText(f"Could not read backup: {str(message).splitlines()[0]}")

        async_bridge.run_background_q(page, work=work, on_success=on_success, on_error=on_error)

    restore_button.clicked.connect(_on_restore)

    # -- Pricing tab ----------------------------------------------------
    pricing_scroll, pricing_layout = _scroll_wrap()
    pricing_box = _section(pricing_layout, "Service pricing matrix", "Read-only fee, SLA, and document reference.")
    pricing_combo = QComboBox()
    pricing_combo.setObjectName("qt-settings-pricing-service")
    pricing_box.addWidget(pricing_combo)
    pricing_table = make_table()
    pricing_table.setObjectName("qt-settings-pricing")
    pricing_box.addWidget(pricing_table, 1)
    pricing_layout.addStretch(1)
    tabs.addTab(pricing_scroll, "Pricing")
    page.pricing_service_combo = pricing_combo  # type: ignore[attr-defined]
    page.pricing_table = pricing_table  # type: ignore[attr-defined]

    def _pricing_rows(service_type: str) -> list[dict]:
        try:
            rows = db.get_pricing_matrix(service_type=service_type)
        except Exception:
            log.warning("Qt pricing load failed", exc_info=True)
            return []
        out: list[dict] = []
        for row in rows or []:
            try:
                monthly = row.get("monthly_fee") or 0
                annual = row.get("annual_fee") or 0
                out.append(
                    {
                        "range": row.get("transaction_range") or "",
                        "monthly": f"{int(monthly):,}",
                        "annual": f"{int(annual):,}",
                        "sla": str(row.get("sla_hours") or ""),
                        "headcount": str(row.get("headcount") or ""),
                        "docs": row.get("required_docs") or "",
                    }
                )
            except Exception:
                continue
        return out

    def refresh_pricing() -> None:
        try:
            from skyadmin_pro.config import PRICING_DEFAULT_SERVICE

            services = db.list_pricing_service_types() or [PRICING_DEFAULT_SERVICE]
        except Exception:
            services = ["General"]
        current = pricing_combo.currentText().strip()
        pricing_combo.blockSignals(True)
        try:
            pricing_combo.clear()
            pricing_combo.addItems([str(s) for s in services])
            if current and current in [str(s) for s in services]:
                pricing_combo.setCurrentText(current)
        finally:
            pricing_combo.blockSignals(False)
        service = pricing_combo.currentText().strip() or (str(services[0]) if services else "General")
        set_table_rows(pricing_table, PRICING_COLUMNS, _pricing_rows(service))

    page.refresh_pricing = refresh_pricing  # type: ignore[attr-defined]
    pricing_combo.currentTextChanged.connect(lambda _text: refresh_pricing())

    # -- Appearance tab -------------------------------------------------
    appear_scroll, appear_layout = _scroll_wrap()
    appear_box = _section(appear_layout, "Appearance", "Theme applies instantly and is remembered.")
    try:
        from skyadmin_pro.config import DEFAULT_APPEARANCE_MODE, SETTING_APPEARANCE_MODE

        _saved_mode = (db.get_setting(SETTING_APPEARANCE_MODE) or DEFAULT_APPEARANCE_MODE).strip().lower()
    except Exception:
        _saved_mode = "dark"
    if _saved_mode not in ("dark", "light"):
        _saved_mode = "light" if _saved_mode == "system" else "dark"
    appearance_combo = QComboBox()
    appearance_combo.setObjectName("qt-settings-appearance")
    appearance_combo.addItems(["Dark", "Light"])
    appearance_combo.setCurrentText("Light" if _saved_mode == "light" else "Dark")
    appear_box.addWidget(appearance_combo)
    workspace_label = QLabel("")
    workspace_label.setObjectName("qt-settings-workspace")
    workspace_label.setWordWrap(True)
    appear_box.addWidget(workspace_label)
    workspace_button = QPushButton("Change workspace folder…")
    workspace_button.setObjectName("qt-settings-workspace-change")
    appear_box.addWidget(workspace_button)
    appear_layout.addStretch(1)
    tabs.addTab(appear_scroll, "Appearance")
    page.appearance_combo = appearance_combo  # type: ignore[attr-defined]
    page.workspace_label = workspace_label  # type: ignore[attr-defined]
    page.workspace_button = workspace_button  # type: ignore[attr-defined]
    page._appearance_mode = _saved_mode

    def refresh_workspace_label() -> None:
        root = ""
        try:
            if paths is not None and getattr(paths, "root", None) is not None:
                root = str(paths.root)
        except Exception:
            root = ""
        workspace_label.setText(f"Workspace root: {root}" if root else "Workspace root: unavailable")

    page.refresh_workspace_label = refresh_workspace_label  # type: ignore[attr-defined]

    def _on_appearance_change(text: str) -> None:
        from PySide6.QtWidgets import QApplication

        mode = theme_bridge.normalize_mode(text)
        page._appearance_mode = mode
        try:
            app = QApplication.instance()
            if app is not None:
                theme_bridge.apply_theme(app, mode)
        except Exception:
            log.warning("Qt appearance apply failed", exc_info=True)
        try:
            from skyadmin_pro.config import SETTING_APPEARANCE_MODE

            db.set_setting(SETTING_APPEARANCE_MODE, mode)
        except Exception as exc:
            set_status(f"Could not save appearance: {exc}")
            return
        set_status(f"Appearance: {mode}")

    appearance_combo.currentTextChanged.connect(_on_appearance_change)

    def _on_workspace_change() -> None:
        start = ""
        try:
            if paths is not None and getattr(paths, "root", None) is not None:
                start = str(paths.root)
        except Exception:
            start = ""
        folder = QFileDialog.getExistingDirectory(page, "Choose workspace folder", start)
        if not folder:
            return
        try:
            from skyadmin_pro.config import SETTING_WORKSPACE_CUSTOM, SETTING_WORKSPACE_ROOT

            root = str(Path(folder).expanduser().resolve())
            Path(root).mkdir(parents=True, exist_ok=True)
            db.set_setting(SETTING_WORKSPACE_ROOT, root)
            db.set_setting(SETTING_WORKSPACE_CUSTOM, "1")
            workspace_label.setText(f"Workspace root: {root}")
            set_status(f"Workspace: {root}")
        except Exception as exc:
            set_status(f"Could not change workspace: {exc}")

    workspace_button.clicked.connect(_on_workspace_change)

    def refresh() -> None:
        refresh_license()
        refresh_sync()
        refresh_backup_banner()
        refresh_pricing()
        refresh_workspace_label()
        try:
            from skyadmin_pro.config import DEFAULT_APPEARANCE_MODE, SETTING_APPEARANCE_MODE

            saved = (db.get_setting(SETTING_APPEARANCE_MODE) or DEFAULT_APPEARANCE_MODE).strip().lower()
            normalized = theme_bridge.normalize_mode(saved)
            page._appearance_mode = normalized
            appearance_combo.blockSignals(True)
            try:
                appearance_combo.setCurrentText("Light" if normalized == "light" else "Dark")
            finally:
                appearance_combo.blockSignals(False)
        except Exception:
            log.warning("Qt settings appearance refresh failed", exc_info=True)

    page.refresh = refresh  # type: ignore[attr-defined]
    refresh()
    page.setProperty("qt_view_id", "settings")
    return page
