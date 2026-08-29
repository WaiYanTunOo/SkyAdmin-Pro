"""Workflow automation: portal upload, client onboarding, and EOD reports."""

from __future__ import annotations

import re
import webbrowser
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from skyadmin_pro.config import CLIENT_WORKSPACE_FOLDERS, DEFAULT_PORTAL_URL, FINANCIAL_DOC_FOLDER_MAP

_RESERVED = re.compile(r'[<>:"/\\|?*]')
# Windows device names can't be folder names (CON, NUL, COM1, ...).
_WIN_DEVICES = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)", re.IGNORECASE)


def client_folder_key(name: str) -> str:
    """Stable comparison key for matching DB client names to existing folders."""
    cleaned = _RESERVED.sub("", (name or "").strip())
    return re.sub(r"\s+", "", cleaned).casefold()


def sanitize_folder_name(name: str) -> str:
    cleaned = _RESERVED.sub("", name.strip())
    cleaned = re.sub(r"\s+", " ", cleaned).rstrip(" .")
    if cleaned in {"", ".", ".."} or _WIN_DEVICES.match(cleaned):
        raise ValueError("Enter a valid client name for the folder.")
    return cleaned


def _index_client_folders(clients_root: Path) -> dict[str, Path]:
    """Map client_folder_key → existing folder path under clients_root."""
    root = Path(clients_root).resolve()
    index: dict[str, Path] = {}
    if not root.is_dir():
        return index
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        key = client_folder_key(entry.name)
        if key and key not in index:
            index[key] = entry
    return index


def resolve_client_folder(
    clients_root: Path,
    client_name: str,
    *,
    create: bool = False,
) -> Path:
    """Resolve a client display name to its workspace folder on disk.

    Tries the sanitized folder name first, then matches existing folders by
    client_folder_key (handles EN/TH names with or without ``/`` separators).
    When *create* is True, creates the standard subfolders if missing.
    """
    root = Path(clients_root).resolve()
    preferred = sanitize_folder_name(client_name)
    preferred_path = (root / preferred).resolve()
    if preferred_path.is_dir() and preferred_path.is_relative_to(root):
        if create:
            _ensure_workspace_subfolders(preferred_path)
        return preferred_path

    key = client_folder_key(client_name)
    for folder_key, folder_path in _index_client_folders(root).items():
        if folder_key == key:
            if create:
                _ensure_workspace_subfolders(folder_path)
            return folder_path

    if create:
        return create_client_workspace(root, client_name)
    raise FileNotFoundError(f"No workspace folder found for client '{client_name.strip()}'.")


def _ensure_workspace_subfolders(folder: Path) -> None:
    for subfolder in CLIENT_WORKSPACE_FOLDERS:
        (folder / subfolder).mkdir(parents=True, exist_ok=True)
    fin_root = folder / "04_Financial_Docs"
    for subfolder_name in FINANCIAL_DOC_FOLDER_MAP.values():
        (fin_root / subfolder_name).mkdir(parents=True, exist_ok=True)


def create_client_workspace(clients_root: Path, client_name: str) -> Path:
    """Create Clients/[Name]/01_Company_Setup, 02_Accounting, 03_Visa, 04_Financial_Docs. Idempotent."""
    root = Path(clients_root).resolve()
    try:
        existing = resolve_client_folder(root, client_name, create=False)
        _ensure_workspace_subfolders(existing)
        return existing
    except FileNotFoundError:
        pass
    folder = (root / sanitize_folder_name(client_name)).resolve()
    if folder == root or not folder.is_relative_to(root):
        raise ValueError("Enter a valid client name for the folder.")
    _ensure_workspace_subfolders(folder)
    return folder


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
    except Exception:
        pass
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


def format_eod_report(
    tasks: list[dict],
    pipeline: list[dict] | None = None,
    when: date | None = None,
) -> str:
    stamp = when or date.today()
    header = f"SkyAdmin Pro — EOD Report\n{stamp.strftime('%d %B %Y')}"
    if not tasks and not pipeline:
        return f"{header}\n\nNo tasks or pipeline steps completed today."

    sections = [header, ""]
    if tasks:
        ordered = sorted(tasks, key=lambda item: item.get("completed_at") or "")
        sections.append(f"Completed today ({len(ordered)}):")
        sections.append("")
        for index, task in enumerate(ordered, start=1):
            client = (task.get("client_name") or "").strip() or "Unassigned"
            title = (task.get("title") or "Task").strip()
            sections.append(f"{index}. {client}: {title} - Completed")
    if pipeline:
        sections.append("")
        sections.append(f"Pipeline completed today ({len(pipeline)}):")
        sections.append("")
        for index, item in enumerate(pipeline, start=1):
            client = (item.get("client_name") or "").strip() or "Unassigned"
            service = (item.get("service") or "Service").strip()
            sections.append(f"{index}. {client}: {service} - Pipeline complete")
    return "\n".join(sections)
