from __future__ import annotations

import re
from pathlib import Path

from skyadmin_pro.config import CLIENT_WORKSPACE_FOLDERS, FINANCIAL_DOC_FOLDER_MAP

from ._const_0 import _RESERVED
from ._const_1 import _WIN_DEVICES


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
