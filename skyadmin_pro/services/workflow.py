"""Workflow automation: portal upload, client onboarding, and EOD reports."""

from __future__ import annotations

import re
import webbrowser
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from skyadmin_pro.config import CLIENT_WORKSPACE_FOLDERS, DEFAULT_PORTAL_URL

_RESERVED = re.compile(r'[<>:"/\\|?*]')


def sanitize_folder_name(name: str) -> str:
    cleaned = _RESERVED.sub("", name.strip())
    cleaned = re.sub(r"\s+", " ", cleaned).rstrip(" .")
    if cleaned in {"", ".", ".."}:
        raise ValueError("Enter a valid client name for the folder.")
    return cleaned


def create_client_workspace(clients_root: Path, client_name: str) -> Path:
    """Create Clients/[Name]/01_Company_Setup, 02_Accounting, 03_Visa. Idempotent."""
    root = Path(clients_root).resolve()
    folder = (root / sanitize_folder_name(client_name)).resolve()
    if folder == root or not folder.is_relative_to(root):
        raise ValueError("Enter a valid client name for the folder.")
    for subfolder in CLIENT_WORKSPACE_FOLDERS:
        (folder / subfolder).mkdir(parents=True, exist_ok=True)
    return folder


def normalize_portal_url(url: str | None) -> str:
    text = (url or "").strip() or DEFAULT_PORTAL_URL
    raw_scheme = text.split(":", 1)[0].lower() if ":" in text else ""
    if raw_scheme.isalpha() and raw_scheme not in {"http", "https"}:
        raise ValueError("Portal URL must start with http:// or https://")
    if "://" not in text:
        text = "https://" + text
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Portal URL must start with http:// or https://")
    return text


def copy_to_clipboard(text: str, tk_window=None) -> None:
    try:
        import pyperclip

        pyperclip.copy(text)
        return
    except Exception:
        pass
    if tk_window is not None:
        tk_window.clipboard_clear()
        tk_window.clipboard_append(text)
        tk_window.update_idletasks()
        return
    raise RuntimeError("Clipboard is unavailable. Install pyperclip or use the desktop app window.")


def open_portal_and_copy_path(file_path: Path, portal_url: str | None, tk_window=None) -> str:
    """Copy the file's absolute path and open the portal in the default browser."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    absolute = str(file_path.resolve())
    copy_to_clipboard(absolute, tk_window=tk_window)
    webbrowser.open(normalize_portal_url(portal_url))
    return absolute


def format_eod_report(tasks: list[dict], when: date | None = None) -> str:
    stamp = when or date.today()
    header = f"SkyAdmin Pro — EOD Report\n{stamp.strftime('%d %B %Y')}"
    if not tasks:
        return f"{header}\n\nNo tasks marked completed today."

    ordered = sorted(tasks, key=lambda item: item.get("completed_at") or "")
    lines = [header, "", f"Completed today ({len(ordered)}):", ""]
    for index, task in enumerate(ordered, start=1):
        client = (task.get("client_name") or "").strip() or "Unassigned"
        title = (task.get("title") or "Task").strip()
        lines.append(f"{index}. {client}: {title} - Completed")
    return "\n".join(lines)
