from __future__ import annotations

import webbrowser
from pathlib import Path
from urllib.parse import urlparse

from skyadmin_pro.config import DEFAULT_PORTAL_URL

from .funcs_0 import _index_client_folders, client_folder_key, create_client_workspace, sanitize_folder_name


def repair_client_workspaces(clients_root: Path, client_names: list[str]) -> dict[str, int | list[str]]:
    """Ensure every client has a workspace folder; link to existing folders when possible."""
    linked: list[str] = []
    created: list[str] = []
    failed: list[str] = []
    root = Path(clients_root).resolve()
    index = _index_client_folders(root)
    for name in client_names:
        clean = (name or "").strip()
        if not clean:
            continue
        preferred = sanitize_folder_name(clean)
        key = client_folder_key(clean)
        try:
            if (root / preferred).is_dir():
                create_client_workspace(root, clean)
                continue
            if key in index:
                folder = create_client_workspace(root, clean)
                if folder.name != preferred:
                    linked.append(clean)
                continue
            before = set(index)
            folder = create_client_workspace(root, clean)
            index = _index_client_folders(root)
            if key not in before:
                created.append(clean)
            elif folder.name != preferred:
                linked.append(clean)
        except Exception:
            failed.append(clean)
    return {
        "total": len([n for n in client_names if (n or "").strip()]),
        "linked": len(linked),
        "created": len(created),
        "failed": len(failed),
        "linked_names": linked,
        "created_names": created,
        "failed_names": failed,
    }


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
    except Exception as e:
        import logging

        logging.error(f"UI Error: {e}")
    if tk_window is not None:
        try:
            tk_window.clipboard_clear()
            tk_window.clipboard_append(text)
            tk_window.update_idletasks()
            return
        except Exception as exc:
            # Window already closing/destroyed — fall through to the error.
            raise RuntimeError("Clipboard is unavailable right now.") from exc
    raise RuntimeError("Clipboard is unavailable. Install pyperclip or use the desktop app window.")


def open_portal_and_copy_path(file_path: Path, portal_url: str | None, tk_window=None) -> str:
    """Copy the file's absolute path and open the portal in the default browser."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    absolute = str(file_path.resolve())
    copy_to_clipboard(absolute, tk_window=tk_window)
    webbrowser.open(normalize_portal_url(portal_url))
    return absolute
