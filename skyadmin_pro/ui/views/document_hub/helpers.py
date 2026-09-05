"""Shared Document Hub helpers."""

from __future__ import annotations

from pathlib import Path
from tkinter import messagebox

from skyadmin_pro.config import FOLDER_PORTAL_BACKUP, SETTING_PORTAL_URL
from skyadmin_pro.services import file_ops
from skyadmin_pro.services.workflow import open_portal_and_copy_path
from skyadmin_pro.ui.widgets import FeedbackLabel


def open_folder(path: Path, parent=None) -> None:
    try:
        file_ops.open_in_file_manager(path)
    except Exception as exc:
        messagebox.showerror(
            "SkyAdmin Pro",
            f"Could not open folder:\n{path}\n{exc}",
            parent=parent,
        )


def launch_portal(app, path: Path, feedback: FeedbackLabel) -> None:
    url = (app.db.get_setting(SETTING_PORTAL_URL) or "").strip()
    if not url:
        feedback.error("Set the portal URL in Settings first.")
        return
    if not path.is_file():
        feedback.error("That file no longer exists. Refresh and try again.")
        return
    try:
        absolute = open_portal_and_copy_path(path, url, tk_window=app)
    except Exception as exc:
        feedback.error(f"Could not open the portal: {exc}")
        return
    try:
        backup = file_ops.backup_file(path, app.paths.archive / FOLDER_PORTAL_BACKUP)
    except OSError as exc:
        feedback.error(f"Portal opened, but the backup copy failed: {exc}")
        return
    feedback.success(f"Backup saved to {backup.name}. Portal opened — paste with Ctrl+V.\n{absolute}")
    app.set_status("Portal opened — file path on clipboard (backup saved).")
