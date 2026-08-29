"""Local filesystem layout for SkyAdmin Pro.

The workspace root defaults to Documents/SkyAdmin Pro and can be changed
later from Settings. All document-pipeline folders live under that root.
"""

from __future__ import annotations

import sys
from pathlib import Path

from skyadmin_pro.config import (
    APP_NAME,
    FOLDER_ARCHIVE,
    FOLDER_CLIENTS,
    FOLDER_READY,
    FOLDER_STAGING,
    FOLDER_SUPPLIERS,
)


def user_documents_dir() -> Path:
    """Return the real Documents folder (honours OneDrive/Known-Folder
    redirection), falling back to ~/Documents, then the home directory."""
    if sys.platform == "win32":
        try:
            import ctypes
            import uuid

            # FOLDERID_Documents as a little-endian binary GUID.
            folder_id = (ctypes.c_ubyte * 16).from_buffer_copy(
                uuid.UUID("{FDD39AD0-238F-46AF-ADB4-6C85480369C7}").bytes_le
            )
            out = ctypes.c_wchar_p()
            hr = ctypes.windll.shell32.SHGetKnownFolderPath(
                ctypes.cast(folder_id, ctypes.c_void_p),
                0,      # flags: default known path for current user
                None,   # hToken: calling process user
                ctypes.byref(out),
            )
            value = out.value if hr == 0 else None
            if out.value:
                ctypes.windll.ole32.CoTaskMemFree(out)
            if value:
                return Path(value)
        except Exception:
            pass  # fall back below
    home = Path.home()
    documents = home / "Documents"
    return documents if documents.exists() else home


def default_workspace_root() -> Path:
    """Customer data (documents) lives next to the exe when frozen;
    during development it lives in Documents like any normal project."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "Workspace"
    return user_documents_dir() / APP_NAME


def app_data_dir() -> Path:
    """Directory that holds the SQLite database (next to the workspace, under home)."""
    path = Path.home() / ".skyadmin_pro"
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    return app_data_dir() / "skyadmin_pro.db"


class WorkspacePaths:
    """Resolved paths for the document pipeline. Call ensure() after construction."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root else default_workspace_root()

    @property
    def staging(self) -> Path:
        return self.root / FOLDER_STAGING

    @property
    def ready_to_upload(self) -> Path:
        return self.root / FOLDER_READY

    @property
    def archive(self) -> Path:
        return self.root / FOLDER_ARCHIVE

    @property
    def clients(self) -> Path:
        return self.root / FOLDER_CLIENTS

    @property
    def suppliers(self) -> Path:
        return self.root / FOLDER_SUPPLIERS

    def ensure(self) -> None:
        """Create the workspace root and standard pipeline folders if missing."""
        for folder in (
            self.root,
            self.staging,
            self.ready_to_upload,
            self.archive,
            self.clients,
            self.suppliers,
        ):
            folder.mkdir(parents=True, exist_ok=True)
